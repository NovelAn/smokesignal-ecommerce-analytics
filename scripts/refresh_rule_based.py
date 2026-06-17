#!/usr/bin/env python3
"""二刷降级到 rule-based 的客户，强制重走 LLM（persona + sentiment + intent）。

场景：token 余额恢复 / AI 接口修复 / 分析逻辑升级后，
把之前因 token 不足或接口异常被迫降级 rule-based 的客户重新跑 AI。

识别降级（buyer_ai_analysis_cache 表）：
  persona_method   = 'Rule-Based'   → persona 降级
  sentiment_method = 'rule_based'   → sentiment/intent 降级

用法（用主仓库 venv，worktree/主仓库均可）：
  python scripts/refresh_rule_based.py                  # 二刷所有降级客户
  python scripts/refresh_rule_based.py --type persona    # 只刷 persona 降级
  python scripts/refresh_rule_based.py --type sentiment  # 只刷 sentiment 降级
  python scripts/refresh_rule_based.py --limit 50        # 最多刷 50 个
  python scripts/refresh_rule_based.py --dry-run         # 只列名单不执行

每个客户按它的降级情况精准刷（只 persona 降级就刷 persona，省 token）。
结束后报告"仍降级"的客户 = AI 还没恢复（token/接口），稳定后再跑一次。
"""
import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

# --- 定位主仓库 backend/.env（worktree 没有，被 gitignore）---
_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_env() -> str | None:
    # 1. 当前仓库 backend/.env（主仓库场景）
    p = os.path.abspath(os.path.join(_HERE, "..", "backend", ".env"))
    if os.path.exists(p):
        return p
    # 2. worktree: git-common-dir 推导主仓库根（与 start-backend.sh 同逻辑）
    try:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=_HERE, stderr=subprocess.DEVNULL,
        ).decode().strip()
        common = os.path.abspath(os.path.join(_HERE, common))
        main_root = os.path.dirname(common)
        p2 = os.path.join(main_root, "backend", ".env")
        if os.path.exists(p2):
            return p2
    except Exception:
        pass
    return None


_env = _find_env()
if _env:
    from dotenv import load_dotenv
    load_dotenv(_env)
else:
    print("⚠️  未找到 backend/.env，DB 查询会失败", file=sys.stderr)

sys.path.insert(0, os.path.join(_HERE, ".."))
from backend.config import settings  # noqa: E402
from backend.database import Database  # noqa: E402


def fetch_degraded(db: Database, refresh_type: str) -> tuple[set, set]:
    """返回 (persona_降级集合, sentiment_降级集合)。"""
    persona = set()
    sentiment = set()
    if refresh_type in ("persona", "all"):
        persona = {r["buyer_nick"] for r in db.execute_query(
            "SELECT buyer_nick FROM buyer_ai_analysis_cache WHERE persona_method='Rule-Based'")}
    if refresh_type in ("sentiment", "all"):
        sentiment = {r["buyer_nick"] for r in db.execute_query(
            "SELECT buyer_nick FROM buyer_ai_analysis_cache WHERE sentiment_method='rule_based'")}
    return persona, sentiment


def main() -> None:
    ap = argparse.ArgumentParser(
        description="二刷降级 rule-based 的客户，强制重走 LLM。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--type", choices=["all", "persona", "sentiment"], default="all")
    ap.add_argument("--limit", type=int, default=0, help="最多刷 N 个，0=不限")
    ap.add_argument("--dry-run", action="store_true", help="只列名单不执行")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--backend-url", default=os.getenv("BACKEND_URL", "http://localhost:8000/api/v2"))
    ap.add_argument("--http-timeout", type=int, default=400)
    args = ap.parse_args()

    db = Database(db_name=settings.db_name_to_use)
    persona_deg, sentiment_deg = fetch_degraded(db, args.type)
    all_nicks = persona_deg | sentiment_deg
    if args.limit and len(all_nicks) > args.limit:
        all_nicks = set(sorted(all_nicks)[: args.limit])

    def type_for(nick: str) -> str:
        p, s = nick in persona_deg, nick in sentiment_deg
        return "all" if (p and s) else ("persona" if p else "sentiment")

    print(f"降级客户: persona={len(persona_deg)}, sentiment={len(sentiment_deg)}, 并集={len(all_nicks)}")
    if not all_nicks:
        print("✅ 没有降级客户，无需二刷")
        return
    for n in sorted(all_nicks):
        print(f"  - {n}  (刷 {type_for(n)})")
    if args.dry_run:
        print("\n--dry-run，不执行")
        return

    def refresh(nick: str):
        t = type_for(nick)
        url = (f"{args.backend_url}/buyers/{urllib.parse.quote(nick, safe='')}"
               f"/force-refresh?refresh_type={t}&reanalyze=true&analysis_mode=full")
        req = urllib.request.Request(url, method="POST")
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=args.http_timeout) as r:
                json.loads(r.read())
            return nick, True, round(time.time() - t0, 1), None
        except Exception as e:
            return nick, False, round(time.time() - t0, 1), str(e)[:100]

    print(f"\n=== 并发二刷（{args.concurrency} 并发）===")
    ok = fail = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for res in ex.map(refresh, sorted(all_nicks)):
            nick = res[0]
            if res[1]:
                print(f"  ✅ {nick} ({res[2]}s)")
                ok += 1
            else:
                print(f"  ⚠️  {nick} ({res[2]}s) {res[3]}  (后端可能仍在跑)")
                fail += 1
    print(f"\nHTTP: {ok} 成功 / {fail} 超时(后端可能仍在跑)")

    # 轮询验证：直到降级客户全部转 AI，或确认仍降级
    nicks = list(all_nicks)
    ph = ",".join(["%s"] * len(nicks))

    def still_degraded():
        sp = {r["buyer_nick"] for r in db.execute_query(
            f"SELECT buyer_nick FROM buyer_ai_analysis_cache "
            f"WHERE persona_method='Rule-Based' AND buyer_nick IN ({ph})", tuple(nicks))} if persona_deg else set()
        ss = {r["buyer_nick"] for r in db.execute_query(
            f"SELECT buyer_nick FROM buyer_ai_analysis_cache "
            f"WHERE sentiment_method='rule_based' AND buyer_nick IN ({ph})", tuple(nicks))} if sentiment_deg else set()
        return sp, ss

    print("\n=== 轮询验证 ===")
    for _ in range(15):
        sp, ss = still_degraded()
        if not sp and not ss:
            break
        print(f"  仍降级: persona {len(sp)}, sentiment {len(ss)}，等 20s 后端跑完...")
        time.sleep(20)

    sp, ss = still_degraded()
    print("\n=== 最终结果 ===")
    if sp or ss:
        print("⚠️  仍降级（AI 可能还没恢复，token/接口稳定后再跑一次本脚本）：")
        for n in sorted(sp):
            print(f"    persona:   {n}")
        for n in sorted(ss):
            print(f"    sentiment: {n}")
    else:
        print("✅ 全部重走 LLM 完成")


if __name__ == "__main__":
    main()
