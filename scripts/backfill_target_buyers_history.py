"""
Production backfill for target_buyers_precomputed_history.

对范围内每一天 d 调用 refresh_target_buyers_asof(d), 把当天真 ASOF 状态
写入 history 表。一次性脚本, 跑完即可删除。

特性:
  - 可恢复: 进度持久化到 logs/backfill_progress.json, 中断后从上次成功日继续
  - 重试: 每天最多 3 次重试, 指数退避 5/15/45s
  - 避峰: 默认 02:00-06:00 才跑, --force 绕过
  - 干跑: --dry-run 只输出计划不写库
  - 限速: --rate-limit 控制每天间隔 (默认 0s, 因 procedure 内部已重)

用法:
    # 默认范围 (2025-04-01 ~ CURDATE()-1)
    PYTHONPATH=. python scripts/backfill_target_buyers_history.py

    # 自定义范围 + 干跑
    PYTHONPATH=. python scripts/backfill_target_buyers_history.py \\
        --start 2025-04-01 --end 2025-04-30 --dry-run

    # 强制白天跑
    PYTHONPATH=. python scripts/backfill_target_buyers_history.py --force

    # 跳到指定日期 (进度跳过已成功日)
    PYTHONPATH=. python scripts/backfill_target_buyers_history.py --resume-from 2025-05-15
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Iterator, Optional

# Windows stdout encoding fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from backend.database.connection import Database

LOG = logging.getLogger("backfill_history")

# === 常量 ===
DEFAULT_START = date(2025, 4, 1)
DEFAULT_END_OFFSET_DAYS = 1  # 默认跑昨天 (T-1, 与主表 procedure 行为一致)
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (5, 15, 45)
OFFPEAK_START = dt_time(2, 0)   # 02:00
OFFPEAK_END = dt_time(6, 0)     # 06:00
PROGRESS_DIR = Path("logs")
PROGRESS_FILE = PROGRESS_DIR / "backfill_progress.json"


# === State (frozen dataclass for immutability) ===
@dataclass(frozen=True)
class ProgressState:
    """持久化的回填进度状态。"""

    last_success_date: Optional[str] = None
    failed_dates: tuple[str, ...] = ()
    started_at: Optional[str] = None
    last_updated_at: Optional[str] = None
    total_success: int = 0
    total_failed: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "ProgressState":
        data = json.loads(raw)
        return cls(
            last_success_date=data.get("last_success_date"),
            failed_dates=tuple(data.get("failed_dates", [])),
            started_at=data.get("started_at"),
            last_updated_at=data.get("last_updated_at"),
            total_success=int(data.get("total_success", 0)),
            total_failed=int(data.get("total_failed", 0)),
        )


@dataclass(frozen=True)
class RunConfig:
    """CLI 参数汇总。"""

    start: date
    end: date
    dry_run: bool
    force: bool
    resume_from: Optional[date]
    rate_limit_seconds: float


# === 进度持久化 ===
def load_progress() -> ProgressState:
    """读取进度文件; 不存在则返回空状态。"""
    if not PROGRESS_FILE.exists():
        return ProgressState()
    try:
        return ProgressState.from_json(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        LOG.warning("进度文件损坏, 重新开始: %s", exc)
        return ProgressState()


def save_progress(state: ProgressState) -> None:
    """原子写入进度文件 (tmp + replace)。"""
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = PROGRESS_FILE.with_suffix(".json.tmp")
    tmp.write_text(state.to_json(), encoding="utf-8")
    tmp.replace(PROGRESS_FILE)


def update_progress(state: ProgressState, **changes) -> ProgressState:
    """返回新 state (不可变)。"""
    return ProgressState(
        last_success_date=changes.get("last_success_date", state.last_success_date),
        failed_dates=changes.get("failed_dates", state.failed_dates),
        started_at=changes.get("started_at", state.started_at),
        last_updated_at=datetime.now().isoformat(timespec="seconds"),
        total_success=changes.get("total_success", state.total_success),
        total_failed=changes.get("total_failed", state.total_failed),
    )


# === 日期范围 ===
def daterange(start: date, end: date) -> Iterator[date]:
    """生成 [start, end] 闭区间所有日期。"""
    if end < start:
        raise ValueError(f"end ({end}) < start ({start})")
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def filter_dates(
    all_dates: list[date],
    state: ProgressState,
    resume_from: Optional[date],
) -> list[date]:
    """过滤掉已成功的日期; 应用 --resume-from。"""
    success_set: set[date] = set()
    if state.last_success_date:
        # last_success_date 之后的所有日期都视为未完成 (除重)
        last = date.fromisoformat(state.last_success_date)
        success_set = {last}

    if resume_from:
        all_dates = [d for d in all_dates if d >= resume_from]

    return [d for d in all_dates if d not in success_set]


# === 避峰检查 ===
def is_offpeak(now: datetime) -> bool:
    """当前是否在 02:00-06:00 窗口内。"""
    t = now.time()
    return OFFPEAK_START <= t < OFFPEAK_END


# === Procedure 调用 ===
def call_refresh_asof(db: Database, d: date) -> int:
    """调用 refresh_target_buyers_asof(d), 返回 history 表中该日行数。

    Raises:
        pymysql.MySQLError: procedure 内部失败
    """
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("CALL refresh_target_buyers_asof(%s)", (d,))
            # 验证行数
            cursor.execute(
                "SELECT COUNT(*) AS n FROM target_buyers_precomputed_history "
                "WHERE snapshot_date = %s",
                (d,),
            )
            row = cursor.fetchone()
            n = int(row["n"]) if row else 0
            if n == 0:
                raise RuntimeError(f"procedure reported success but 0 rows for {d}")
            return n


def backfill_one_day(db: Database, d: date) -> int:
    """单日 backfill, 含重试。返回最终行数。"""
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            n = call_refresh_asof(db, d)
            LOG.info("[OK ] %s  rows=%d  attempt=%d", d, n, attempt)
            return n
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS[attempt - 1]
                LOG.warning(
                    "[RETRY] %s  attempt=%d/%d  wait=%ds  err=%s",
                    d, attempt, MAX_RETRIES, wait, exc,
                )
                time.sleep(wait)
            else:
                LOG.error("[FAIL] %s  attempt=%d/%d  err=%s", d, attempt, MAX_RETRIES, exc)
    assert last_exc is not None
    raise last_exc


# === 主流程 ===
def run_backfill(cfg: RunConfig) -> ProgressState:
    """执行完整 backfill, 返回最终进度状态。"""
    state = load_progress()
    if not state.started_at:
        state = update_progress(state, started_at=datetime.now().isoformat(timespec="seconds"))
        save_progress(state)

    all_dates = list(daterange(cfg.start, cfg.end))
    todo = filter_dates(all_dates, state, cfg.resume_from)
    total = len(todo)

    LOG.info("=" * 60)
    LOG.info("Backfill plan")
    LOG.info("  range:        %s -> %s  (%d days)", cfg.start, cfg.end, len(all_dates))
    LOG.info("  remaining:    %d days", total)
    LOG.info("  last success: %s", state.last_success_date or "none")
    LOG.info("  dry-run:      %s", cfg.dry_run)
    LOG.info("  off-peak:     %s  (window %s-%s)",
             is_offpeak(datetime.now()), OFFPEAK_START, OFFPEAK_END)
    LOG.info("=" * 60)

    if total == 0:
        LOG.info("Nothing to do. Exit.")
        return state

    if cfg.dry_run:
        for i, d in enumerate(todo, 1):
            LOG.info("[DRY-RUN] %d/%d  %s", i, total, d)
        return state

    db = Database()
    success_count = 0
    failed: list[str] = list(state.failed_dates)
    new_last_success = state.last_success_date

    for i, d in enumerate(todo, 1):
        # 避峰检查 (--force 绕过)
        if not cfg.force and not is_offpeak(datetime.now()):
            LOG.warning(
                "[OFF-PEAK] 当前时间不在 %s-%s 窗口, 暂停. 用 --force 绕过.",
                OFFPEAK_START, OFFPEAK_END,
            )
            break

        LOG.info("=== %d/%d  %s ===", i, total, d)
        try:
            backfill_one_day(db, d)
            success_count += 1
            new_last_success = d.isoformat()
            failed = [x for x in failed if x != d.isoformat()]
        except Exception:  # noqa: BLE001
            failed.append(d.isoformat())
            LOG.exception("backfill %s failed, 已记录到 failed_dates", d)

        # 实时持久化 (中断可恢复)
        state = update_progress(
            state,
            last_success_date=new_last_success,
            failed_dates=tuple(failed),
            total_success=state.total_success + success_count,
            total_failed=len(failed),
        )
        save_progress(state)
        success_count = 0  # 已在 state.total_success 累计

        if cfg.rate_limit_seconds > 0:
            time.sleep(cfg.rate_limit_seconds)

    # 汇总
    LOG.info("=" * 60)
    LOG.info("Backfill summary")
    LOG.info("  success this run: %d", success_count)
    LOG.info("  failed:           %d  %s", len(failed), failed)
    LOG.info("  last_success:     %s", new_last_success)
    LOG.info("=" * 60)
    return state


def parse_args(argv: Optional[list[str]] = None) -> RunConfig:
    parser = argparse.ArgumentParser(
        description="Backfill target_buyers_precomputed_history 真 ASOF 历史快照",
    )
    parser.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START,
                        help=f"起始日期 (含), 默认 {DEFAULT_START}")
    default_end = (date.today() - timedelta(days=DEFAULT_END_OFFSET_DAYS))
    parser.add_argument("--end", type=date.fromisoformat, default=default_end,
                        help=f"结束日期 (含), 默认 T-{DEFAULT_END_OFFSET_DAYS} = {default_end}")
    parser.add_argument("--dry-run", action="store_true", help="只输出计划, 不写库")
    parser.add_argument("--force", action="store_true", help="绕过避峰检查 (02:00-06:00 窗口)")
    parser.add_argument("--resume-from", type=date.fromisoformat, default=None,
                        help="从指定日期开始 (之前的日期视为已处理)")
    parser.add_argument("--rate-limit", type=float, default=0.0,
                        help="每天跑完后的等待秒数 (默认 0)")
    args = parser.parse_args(argv)

    if args.end > date.today():
        parser.error(f"--end 不能是未来日期: {args.end}")
    if args.rate_limit < 0:
        parser.error("--rate-limit 必须 >= 0")

    return RunConfig(
        start=args.start,
        end=args.end,
        dry_run=args.dry_run,
        force=args.force,
        resume_from=args.resume_from,
        rate_limit_seconds=args.rate_limit,
    )


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-5s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        cfg = parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    try:
        run_backfill(cfg)
    except KeyboardInterrupt:
        LOG.warning("用户中断. 进度已保存, 下次重跑从断点继续.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
