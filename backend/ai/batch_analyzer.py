"""
Batch Analyzer - 批量AI情绪/意图分析

缓存策略: 纯增量更新，无TTL
- 存储数据快照 (analyzed_last_purchase_date, analyzed_last_chat_date)
- 只有新聊天才触发重新分析
- 前提条件: 聊天天数 >= 10

功能:
1. 增量更新: 只分析有新增聊天记录的客户
2. 智能限流: 每分钟最多20次API调用
3. 多级降级: MiniMax M2.7 → DeepSeek → 规则引擎
4. 批量处理: 每批20个客户
"""
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
import threading

from backend.analytics.tag_calculator import TagCalculator
from backend.ai.analyzer_orchestrator import get_analyzer_orchestrator
from backend.ai.model_selection import should_use_deepseek_pro

logger = logging.getLogger(__name__)


class BatchTaskStatus(str, Enum):
    """Batch task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchTask:
    """Batch analysis task"""
    task_id: str
    status: BatchTaskStatus = BatchTaskStatus.PENDING
    total_buyers: int = 0
    processed_buyers: int = 0
    skipped_buyers: int = 0  # 跳过的买家（无需更新）
    failed_buyers: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, calls_per_minute: int = 20):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
        self.lock = threading.Lock()

    def wait(self):
        """Wait if necessary to respect rate limit"""
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_call_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_call_time = time.time()


# 客户发送消息条数阈值（情感分析前提条件，排除客服自动回复）
CHAT_THRESHOLD_MESSAGES = 5


class BatchAnalyzer:
    """
    Batch analyzer for sentiment and intent analysis

    缓存策略: 纯增量更新
    - 前提条件: 聊天条数 >= 10
    - 触发条件: 首次分析 或 有新聊天

    Features:
    - Incremental updates: Only analyze buyers with new chat records
    - Smart rate limiting: Max 20 API calls per minute
    - Multi-level fallback: Zhipu → DeepSeek → Rule-based
    - Batch processing: 20 buyers per batch
    """

    def __init__(
        self,
        rate_limit: int = 20,
        batch_size: int = 20,
        max_workers: int = 3
    ):
        self.rate_limiter = RateLimiter(calls_per_minute=rate_limit)
        self.batch_size = batch_size
        self.max_workers = max_workers

        # Task storage
        self.tasks: Dict[str, BatchTask] = {}
        self.task_lock = threading.Lock()

        # Initialize AI clients
        self._init_ai_clients()

    def _init_ai_clients(self):
        """Initialize AI clients with fallback chain"""
        try:
            from backend.ai.minimax_client import MiniMaxClient
            self.minimax_client = MiniMaxClient()
            logger.info("[BatchAnalyzer] MiniMaxClient initialized")
        except Exception as e:
            logger.warning(f"[BatchAnalyzer] Failed to init MiniMaxClient: {e}")
            self.minimax_client = None

        try:
            from backend.ai.deepseek_client import DeepSeekClient
            self.deepseek_client = DeepSeekClient()
            logger.info("[BatchAnalyzer] DeepSeekClient initialized")
        except Exception as e:
            logger.warning(f"[BatchAnalyzer] Failed to init DeepSeekClient: {e}")
            self.deepseek_client = None

    def get_buyers_needing_analysis(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get buyers that need sentiment analysis (增量更新)

        Criteria:
        1. Has enough customer messages (total_chat_messages >= 5, sender_nick=user_nick)  -- 前提条件
        2. Never analyzed before (sentiment_score IS NULL)
        3. OR has new chats since last analysis (last_chat_date > analyzed_last_chat_date)

        Returns:
            List of buyer dicts with buyer_nick, last_chat_date, total_chat_messages, etc.
        """
        from backend.database import Database
        from backend.config import settings

        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        query = """
            SELECT
                tb.buyer_nick,
                tb.last_chat_date,
                tb.last_purchase_date,
                tb.total_chat_messages,
                tb.chat_frequency_days,
                tb.vip_level,
                tb.historical_net_sales,
                cache.sentiment_score,
                cache.sentiment_label,
                cache.intent_distribution,
                cache.sentiment_analyzed_last_chat_date,
                cache.sentiment_analyzed_at
            FROM target_buyers_precomputed tb
            LEFT JOIN buyer_ai_analysis_cache cache
                ON tb.buyer_nick = cache.buyer_nick
            WHERE tb.total_chat_messages >= %s
            AND (
                cache.buyer_nick IS NULL
                OR cache.sentiment_score IS NULL
                OR tb.last_chat_date > cache.sentiment_analyzed_last_chat_date
                OR (cache.intent_distribution IS NOT NULL AND tb.pre_sale_score = 0 AND tb.post_sale_score = 0)
            )
            ORDER BY
                CASE
                    WHEN tb.vip_level IN ('V3', 'V2') THEN 0
                    WHEN tb.vip_level = 'V1' THEN 1
                    ELSE 2
                END,
                tb.last_chat_date DESC
            LIMIT %s
        """

        buyers = db.execute_query(query, [CHAT_THRESHOLD_MESSAGES, limit])
        logger.info(f"[BatchAnalyzer] Found {len(buyers)} buyers needing analysis (messages>={CHAT_THRESHOLD_MESSAGES})")
        return buyers

    def get_buyers_needing_persona_refresh(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get buyers that need persona refresh."""
        from backend.database import Database
        from backend.config import settings

        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        query = """
            SELECT
                tb.buyer_nick,
                tb.channel,
                tb.buyer_type,
                tb.follow_priority,
                tb.vip_level,
                tb.client_monthly_tag,
                tb.historical_gmv,
                tb.historical_refund,
                tb.historical_net_sales,
                tb.total_orders,
                tb.total_net_orders,
                tb.refund_rate,
                tb.first_purchase_date,
                tb.last_purchase_date,
                tb.rolling_24m_netsales,
                tb.rolling_24m_orders,
                tb.l6m_gmv,
                tb.l6m_netsales,
                tb.l6m_orders,
                tb.l6m_refund_rate,
                tb.l1y_gmv,
                tb.l1y_netsales,
                tb.l1y_orders,
                tb.l1y_refund_rate,
                tb.discount_ratio,
                tb.discount_sensitivity,
                tb.chat_frequency_days,
                tb.first_chat_date,
                tb.last_chat_date,
                tb.l30d_chat_frequency_days,
                tb.l3m_chat_frequency_days,
                tb.avg_chat_interval_days,
                tb.churn_risk,
                tb.city,
                tb.top_category,
                tb.second_category,
                tb.third_category,
                tb.rfm_segment,
                cache.persona_summary,
                cache.persona_analyzed_at,
                cache.persona_analyzed_last_purchase_date,
                cache.persona_analyzed_last_chat_date
            FROM target_buyers_precomputed tb
            LEFT JOIN buyer_ai_analysis_cache cache ON tb.buyer_nick = cache.buyer_nick
            WHERE
                cache.persona_summary IS NULL
                OR (tb.last_purchase_date IS NOT NULL AND (
                    cache.persona_analyzed_last_purchase_date IS NULL
                    OR tb.last_purchase_date > cache.persona_analyzed_last_purchase_date
                ))
                OR (tb.last_chat_date IS NOT NULL AND (
                    cache.persona_analyzed_last_chat_date IS NULL
                    OR tb.last_chat_date > cache.persona_analyzed_last_chat_date
                ))
            ORDER BY
                CASE tb.follow_priority
                    WHEN '紧急' THEN 1
                    WHEN '高' THEN 2
                    WHEN '中' THEN 3
                    ELSE 4
                END,
                CASE
                    WHEN tb.churn_risk = '高' THEN 0
                    WHEN tb.churn_risk = '中' THEN 1
                    ELSE 2
                END,
                CASE
                    WHEN tb.l6m_netsales >= 10000 THEN 0
                    WHEN tb.l6m_netsales >= 3000 THEN 1
                    ELSE 2
                END,
                tb.last_purchase_date DESC
            LIMIT %s
        """

        buyers = db.execute_query(query, [limit])
        logger.info(f"[BatchAnalyzer] Found {len(buyers)} buyers needing persona refresh")
        return buyers

    def _build_persona_profile_data(
        self,
        buyer_nick: str,
        profile: Dict[str, Any],
        chats: List[Dict[str, Any]],
        orders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build the profile payload used by persona analysis."""
        from backend.ai.persona_context import build_persona_profile_data
        return build_persona_profile_data(buyer_nick, profile, chats, [])

        from datetime import datetime as dt

        today = dt.now()

        last_purchase_date = profile.get('last_purchase_date')
        first_purchase_date = profile.get('first_purchase_date')
        last_chat_date = profile.get('last_chat_date')

        days_since_last_purchase = 0
        days_since_last_chat = 0
        avg_repurchase_interval_days = 0

        if last_purchase_date:
            try:
                if isinstance(last_purchase_date, str):
                    last_purchase_date = dt.strptime(last_purchase_date[:19], '%Y-%m-%d %H:%M:%S')
                days_since_last_purchase = (today - last_purchase_date).days
            except:
                pass

        if last_chat_date:
            try:
                if isinstance(last_chat_date, str):
                    last_chat_date = dt.strptime(last_chat_date[:19], '%Y-%m-%d %H:%M:%S')
                days_since_last_chat = (today - last_chat_date).days
            except:
                pass

        total_orders = int(profile.get('total_orders', 0))
        if first_purchase_date and last_purchase_date and total_orders > 1:
            try:
                if isinstance(first_purchase_date, str):
                    first_purchase_date = dt.strptime(first_purchase_date[:19], '%Y-%m-%d %H:%M:%S')
                if isinstance(last_purchase_date, str):
                    last_purchase_date = dt.strptime(last_purchase_date[:19], '%Y-%m-%d %H:%M:%S')
                days_span = (last_purchase_date - first_purchase_date).days
                avg_repurchase_interval_days = round(days_span / (total_orders - 1)) if days_span > 0 else 0
            except:
                pass

        return {
            "user_nick": buyer_nick,
            "buyer_nick": profile.get('buyer_nick'),
            "channel": profile.get('channel'),
            "buyer_type": profile.get('buyer_type'),
            "is_smoker": profile.get('is_smoker', 0),
            "is_vic": profile.get('is_vic', 0),
            "vip_level": profile.get('vip_level', 'Non-VIP'),
            "client_monthly_tag": profile.get('client_monthly_tag'),
            "historical_gmv": float(profile.get('historical_gmv', 0)),
            "historical_refund": float(profile.get('historical_refund', 0)),
            "historical_net_sales": float(profile.get('historical_net_sales', 0)),
            "total_orders": int(profile.get('total_orders', 0)),
            "total_net_orders": int(profile.get('total_net_orders', 0)),
            "refund_rate": float(profile.get('refund_rate', 0)),
            "first_purchase_date": str(profile.get('first_purchase_date', '')) if profile.get('first_purchase_date') else '',
            "last_purchase_date": str(profile.get('last_purchase_date', '')) if profile.get('last_purchase_date') else '',
            "days_since_last_purchase": days_since_last_purchase,
            "days_since_last_chat": days_since_last_chat,
            "avg_repurchase_interval_days": avg_repurchase_interval_days,
            "rolling_24m_netsales": float(profile.get('rolling_24m_netsales', 0)),
            "rolling_24m_orders": int(profile.get('rolling_24m_orders', 0)),
            "l6m_gmv": float(profile.get('l6m_gmv', 0)),
            "l6m_netsales": float(profile.get('l6m_netsales', 0)),
            "l6m_orders": int(profile.get('l6m_orders', 0)),
            "l6m_refund_rate": float(profile.get('l6m_refund_rate', 0)),
            "l1y_gmv": float(profile.get('l1y_gmv', 0)),
            "l1y_netsales": float(profile.get('l1y_netsales', 0)),
            "l1y_orders": int(profile.get('l1y_orders', 0)),
            "l1y_refund_rate": float(profile.get('l1y_refund_rate', 0)),
            "discount_ratio": float(profile.get('discount_ratio', 0)),
            "discount_sensitivity": profile.get('discount_sensitivity', '未知'),
            "chat_frequency_days": int(profile.get('chat_frequency_days', 0)),
            "first_chat_date": str(profile.get('first_chat_date')) if profile.get('first_chat_date') else None,
            "last_chat_date": str(profile.get('last_chat_date')) if profile.get('last_chat_date') else None,
            "l30d_chat_frequency_days": int(profile.get('l30d_chat_frequency_days', 0)),
            "l3m_chat_frequency_days": int(profile.get('l3m_chat_frequency_days', 0)),
            "avg_chat_interval_days": float(profile.get('avg_chat_interval_days', 0)),
            "churn_risk": profile.get('churn_risk', '未知'),
            "city": profile.get('city', 'Unknown'),
            "top_category": profile.get('top_category', 'Unknown'),
            "second_category": profile.get('second_category'),
            "third_category": profile.get('third_category'),
            "chat_history": chats,
            "external_records": [],
            "total_refund_count": int(float(profile.get('historical_refund', 0)) / 1000) if float(profile.get('historical_refund', 0)) > 0 else 0
        }

    def start_persona_refresh_batch(
        self,
        buyer_limit: int = 100,
        task_id: Optional[str] = None
    ) -> str:
        """Start a persona refresh batch task."""
        import uuid

        if task_id is None:
            task_id = f"persona_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        task = BatchTask(
            task_id=task_id,
            status=BatchTaskStatus.PENDING,
            total_buyers=buyer_limit
        )

        with self.task_lock:
            self.tasks[task_id] = task

        thread = threading.Thread(
            target=self._run_persona_refresh_batch,
            args=(task_id, buyer_limit)
        )
        thread.daemon = True
        thread.start()

        logger.info(f"[BatchAnalyzer] Started persona refresh task {task_id}")
        return task_id


    def _run_persona_refresh_batch(self, task_id: str, buyer_limit: int):
        """Run persona refresh batch analysis in the background."""
        from backend.database import Database, BuyerQueries
        from backend.config import settings

        orchestrator = get_analyzer_orchestrator()

        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            task.status = BatchTaskStatus.RUNNING
            task.started_at = datetime.now()

        try:
            buyers = self.get_buyers_needing_persona_refresh(buyer_limit * 2)
            buyers = sorted(
                buyers,
                key=lambda b: (
                    0 if str(b.get('follow_priority')) == '紧急' else 1 if str(b.get('follow_priority')) == '高' else 2 if str(b.get('follow_priority')) == '中' else 3,
                    0 if str(b.get('churn_risk')) == '高' else 1 if str(b.get('churn_risk')) == '中' else 2,
                    -float(b.get('l6m_netsales') or 0),
                    str(b.get('last_purchase_date') or ''),
                )
            )
            buyers = list(reversed(buyers))[:buyer_limit]
            task.total_buyers = len(buyers)

            if not buyers:
                task.status = BatchTaskStatus.COMPLETED
                task.completed_at = datetime.now()
                return

            db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
            worker_count = min(max(4, self.max_workers + 2), len(buyers), 8)

            def process_buyer(buyer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                if self._should_cancel(task_id):
                    return None

                buyer_nick = buyer['buyer_nick']
                try:
                    db = Database(db_name=db_name)
                    query, params = BuyerQueries.get_chat_messages(buyer_nick, limit=30)
                    chats = db.execute_query(query, params)

                    orders_query = """
                        SELECT
                            订单号, 子订单号, 商品名称 as commodity_name, category,
                            成交总金额 as payment, 退款金额 as refund_amount, 退款类型 as refund_status,
                            FP_MD as fp_md, 件数 as quantity, 最后付款时间 as pay_time
                        FROM dunhill_t01_trade_line
                        WHERE 买家昵称 = %s
                        ORDER BY 最后付款时间 DESC
                    """
                    orders = db.execute_query(orders_query, [buyer_nick])

                    profile_data = self._build_persona_profile_data(buyer_nick, buyer, chats, orders)

                    # 统一走 orchestrator（内部 L1=MiniMax-M3 → L2=DeepSeek → L3=Rule-based）
                    # force_refresh=True 确保 batch 跑过的人都重分析
                    result = orchestrator.analyze_buyer_persona(
                        buyer_nick=buyer_nick,
                        profile=profile_data,
                        chats=chats,
                        orders=orders,
                        force_refresh=True
                    )

                    # orchestrator 内部已经做了 ground_persona_analysis_v3 + cache write，无需重复
                    if orchestrator.cache_manager and orchestrator._is_valid_analysis(result):
                        orchestrator.cache_manager.set_persona(buyer_nick, result, profile_data)

                    if orchestrator.cache_manager and orchestrator._is_valid_analysis(result):
                        orchestrator.cache_manager.set_persona(buyer_nick, result, profile_data)

                    return result
                except Exception as e:
                    logger.error(f"[BatchAnalyzer] Persona failed for {buyer_nick}: {e}")
                    return {"__error__": True, "buyer_nick": buyer_nick}

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_map = {executor.submit(process_buyer, buyer): buyer for buyer in buyers}

                for future in as_completed(future_map):
                    if self._should_cancel(task_id):
                        self._mark_cancelled(task_id)
                        logger.info(f"[BatchAnalyzer] Persona task {task_id} cancelled during processing")
                        return

                    result = future.result()
                    if not result:
                        continue
                    if result.get("__error__"):
                        task.failed_buyers += 1
                        continue

                    task.results.append(result)
                    task.processed_buyers += 1
                    logger.debug(
                        f"[BatchAnalyzer] Persona processed {result.get('buyer_nick')} "
                        f"({task.processed_buyers}/{task.total_buyers})"
                    )

            task.status = BatchTaskStatus.COMPLETED
            task.completed_at = datetime.now()
            logger.info(f"[BatchAnalyzer] Persona task {task_id} completed: {task.processed_buyers} processed, {task.failed_buyers} failed")

        except Exception as e:
            logger.error(f"[BatchAnalyzer] Persona task {task_id} failed: {e}")
            task.status = BatchTaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
    def get_buyer_chats(
        self,
        buyer_nick: str,
        limit: int = 50,
        since_msg_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent chat messages for a buyer.

        Args:
            buyer_nick: 买家昵称
            limit: 返回消息数上限
            since_msg_time: 增量起点（仅返回该时间之后的聊天）。
                None 表示读全量历史；提供 datetime 表示增量模式。
        """
        from backend.database import Database, BuyerQueries
        from backend.config import settings

        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        query, params = BuyerQueries.get_chat_messages(buyer_nick, limit, since_msg_time)
        return db.execute_query(query, params)

    def analyze_single_buyer(
        self,
        buyer_nick: str,
        chats: List[Dict[str, Any]],
        is_incremental: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze sentiment and intent for a single buyer

        统一调用接口（与 DeepSeek / MiniMax 同方法签名）:
            L1: MiniMax-M3（首选，月订阅制省 token）
            L2: DeepSeek（备选，按 token 计费）
            L3: Rule-based（兜底）

        两个模型都暴露同一个 analyze_sentiment_intent(buyer_nick, messages, is_incremental) 接口，
        返回字段完全一致（sentiment_score / sentiment_label / intent_distribution /
        dominant_intent / complaint_count）。Python 后处理（_merge_intent_distribution /
        _dominant_intent / calculate_intent_scores / _extract_keywords）共用一套，保证两个模型
        输出 schema 100% 一致。

        Returns:
            {
                "buyer_nick": str,
                "sentiment_score": float (0-1),
                "sentiment_label": str (Positive/Neutral/Negative),
                "intent_distribution": dict,
                "dominant_intent": str,
                "pre_sale_keywords": list,
                "post_sale_keywords": list,
                "complaint_count": int,
                "sentiment_method": str (minimax_m3 / deepseek / rule_based)
            }
        """
        if not chats:
            return self._default_analysis(buyer_nick, "no_chats")

        # Extract buyer messages only
        buyer_messages = [
            chat.get('content', '')
            for chat in chats
            if chat.get('sender_nick') == buyer_nick and chat.get('content')
        ]

        if not buyer_messages:
            return self._default_analysis(buyer_nick, "no_buyer_messages")

        # ===== L1: MiniMax-M3（首选，月订阅制省 token）=====
        if self.minimax_client:
            try:
                self.rate_limiter.wait()
                logger.debug(f"[BatchAnalyzer] Analyzing {buyer_nick} with MiniMax-M3 (L1)")

                ai_result = self.minimax_client.analyze_sentiment_intent(
                    buyer_nick,
                    buyer_messages[:20],
                    is_incremental=is_incremental
                )
                logger.info(f"[BatchAnalyzer] MiniMax-M3 analysis completed for {buyer_nick}")
                return self._post_process_sentiment(
                    buyer_nick, buyer_messages, ai_result, method='minimax_m3'
                )

            except Exception as e:
                logger.warning(f"[BatchAnalyzer] MiniMax-M3 failed for {buyer_nick}, fallback to DeepSeek: {e}")

        # ===== L2: DeepSeek（备选，按 token 计费）=====
        if self.deepseek_client:
            try:
                self.rate_limiter.wait()
                logger.info(f"[BatchAnalyzer] Analyzing {buyer_nick} with DeepSeek (L2 fallback)")

                ai_result = self.deepseek_client.analyze_sentiment_intent(
                    buyer_nick,
                    buyer_messages[:20],
                    is_incremental=is_incremental
                )
                logger.info(f"[BatchAnalyzer] DeepSeek analysis completed for {buyer_nick}")
                return self._post_process_sentiment(
                    buyer_nick, buyer_messages, ai_result, method='deepseek'
                )

            except Exception as e:
                logger.warning(f"[BatchAnalyzer] DeepSeek failed for {buyer_nick}, fallback to rule-based: {e}")

        # ===== L3: Rule-based（兜底）=====
        return self._rule_based_analysis(buyer_nick, buyer_messages)

    def _post_process_sentiment(
        self,
        buyer_nick: str,
        buyer_messages: List[str],
        ai_result: Dict[str, Any],
        method: str
    ) -> Dict[str, Any]:
        """
        统一的情感意图后处理（MiniMax 和 DeepSeek 共用）

        输入：AI 客户端返回的 {sentiment_score, sentiment_label, intent_distribution,
              dominant_intent, complaint_count} 字段（两个客户端已对齐）。
        输出：补充 _merge_intent_distribution / calculate_intent_scores / _extract_keywords
              三个本地增强，最终结构完全一致，sentiment_method 由 method 决定。

        Args:
            buyer_nick: 买家昵称
            buyer_messages: 买家消息原文列表（用于本地关键词增强）
            ai_result: AI 返回的原始结果（必须包含 sentiment_score / sentiment_label /
                       intent_distribution / dominant_intent / complaint_count）
            method: 'minimax_m3' 或 'deepseek'，写入 sentiment_method 字段

        Returns:
            完整的 buyer 分析结果 dict
        """
        # 1. AI 原始字段
        intent_dist = dict(ai_result.get('intent_distribution') or {})

        # 2. 本地关键词增强（merge AI 结果与本地强关键词信号，避免 AI 漏判售后/投诉）
        merged_intent = self._merge_intent_distribution(intent_dist, buyer_messages)

        # 3. 重新计算 dominant_intent（merged 之后为准）
        dominant_intent = self._dominant_intent(merged_intent)

        # 4. 准备 result
        result = {
            "buyer_nick": buyer_nick,
            "analyzed_at": datetime.now(),
            "sentiment_score": ai_result.get('sentiment_score', 0.5),
            "sentiment_label": ai_result.get('sentiment_label', 'Neutral'),
            "intent_distribution": merged_intent,
            "dominant_intent": dominant_intent,
            "complaint_count": merged_intent.get('Complaint', ai_result.get('complaint_count', 0)),
            "sentiment_method": method,
        }

        # 5. 计算 pre_sale / post_sale score
        intent_scores = TagCalculator.calculate_intent_scores(merged_intent)
        result['pre_sale_score'] = intent_scores['pre_sale_score']
        result['post_sale_score'] = intent_scores['post_sale_score']

        # 6. 提取关键词（与 buyer_messages 一致，不依赖 AI 返回）
        result['pre_sale_keywords'] = self._extract_keywords(buyer_messages, 'pre_sale')
        result['post_sale_keywords'] = self._extract_keywords(buyer_messages, 'post_sale')

        return result

    def _dominant_intent(self, intent_dist: Dict[str, int]) -> str:
        """Return dominant canonical intent, ignoring non-intent metadata."""
        canonical = {
            key: int(intent_dist.get(key, 0) or 0)
            for key in [
                "Pre-sale Inquiry",
                "Post-sale Support",
                "Logistics",
                "Usage Guide",
                "Complaint",
            ]
        }
        if max(canonical.values()) > 0:
            return max(canonical.items(), key=lambda x: x[1])[0]
        return 'Unknown'

    def _merge_intent_distribution(
        self,
        intent_dist: Dict[str, Any],
        messages: List[str]
    ) -> Dict[str, int]:
        """
        Merge AI intent distribution with strict local keyword signals.

        AI providers often undercount post-sale support when a customer has both
        product questions and service/defect follow-ups. Use local signals as a
        floor, not only as an all-zero fallback.
        """
        canonical_keys = [
            "Pre-sale Inquiry",
            "Post-sale Support",
            "Logistics",
            "Usage Guide",
            "Complaint",
        ]
        normalized = {
            key: int((intent_dist or {}).get(key, 0) or 0)
            for key in canonical_keys
        }

        local = self._classify_intents_by_keywords(messages)
        merged = {
            key: max(normalized.get(key, 0), local.get(key, 0))
            for key in canonical_keys
        }

        if sum(normalized.values()) == 0 and sum(local.values()) > 0:
            logger.info("[BatchAnalyzer] Repaired empty intent distribution with local keyword classifier")
        elif merged != normalized:
            logger.info("[BatchAnalyzer] Augmented intent distribution with local keyword classifier")

        return merged

    def _classify_intents_by_keywords(self, messages: List[str]) -> Dict[str, int]:
        pre_sale_keywords = [
            '价格', '多少钱', '有货', '现货', '库存', '尺寸', '尺码', '颜色',
            '款式', '推荐', '新款', '上市', '还有吗', '链接', '双面', '材质',
            '面料', '羊绒', '骆驼绒', '标识', '徽标', 'ad标', '长尾标',
            '适合', '合身', '多大', '腰围', '胸围', '可以买吗', '怎么买'
        ]
        post_sale_keywords = [
            '退货', '退了', '退款', '退一下', '换货', '换成', '调换', '维修',
            '保修', '发票', '收到', '收到了', '售后', '售后服务', '裁袖',
            '裁一下', '修改', '改袖', '改裤脚', '签收', '寄到', '瑕疵',
            '划痕', '黑点', '小瑕疵', '包边', '带头', '不舒服', '不合适',
            '不想要', '发错', '少发', '漏发', '色差', '掉色', '褪色',
            '破损', '坏了', '有问题', '质量问题', '做工', '污渍'
        ]
        logistics_keywords = [
            '物流', '快递', '发货', '发出', '发了吗', '运单', '单号',
            '顺丰', '什么时候到', '配送', '寄出', '寄到', '签收', '地址'
        ]
        usage_keywords = [
            '怎么用', '如何使用', '保养', '清洗', '维护', '说明', '教程',
            '安装', '使用方法', '护理'
        ]
        strong_complaint_keywords = ['投诉', '差评', '举报', '315', '消费者协会', '工商', '找经理']
        dissatisfaction_keywords = [
            '太差', '质量差', '很差', '垃圾', '骗子', '骗人', '假的', '假货', '欺骗',
            '失望', '不满', '不满意', '太慢', '态度差', '服务差', '差的', '不好用',
            '质量太差', '质量不好', '做工差', '掉色', '褪色', '破损', '坏了', '有问题',
            '差劲', '太差了', '质量太差了', '差评', '给差评'
        ]

        counts = {
            "Pre-sale Inquiry": 0,
            "Post-sale Support": 0,
            "Logistics": 0,
            "Usage Guide": 0,
            "Complaint": 0,
        }

        for message in messages:
            text = (message or '').lower()
            if not text:
                continue

            has_complaint = (
                any(kw in text for kw in strong_complaint_keywords)
                or any(kw in text for kw in dissatisfaction_keywords)
            )
            has_post_sale = any(kw in text for kw in post_sale_keywords)
            has_logistics = any(kw in text for kw in logistics_keywords)
            has_usage = any(kw in text for kw in usage_keywords)
            has_pre_sale = any(kw.lower() in text for kw in pre_sale_keywords)

            if has_complaint:
                counts["Complaint"] += 1
            if has_post_sale:
                counts["Post-sale Support"] += 1
            if has_logistics:
                counts["Logistics"] += 1
            if has_usage:
                counts["Usage Guide"] += 1
            if has_pre_sale:
                counts["Pre-sale Inquiry"] += 1

        return counts

    def _rule_based_analysis(
        self,
        buyer_nick: str,
        messages: List[str]
    ) -> Dict[str, Any]:
        """Rule-based sentiment and intent analysis (final fallback)"""
        positive_words = ['好', '喜欢', '满意', '感谢', '谢谢', '不错', '很好', '棒', '赞']
        negative_words = ['差', '不好', '失望', '投诉', '退货', '退款', '问题', '坏的', '不喜欢']

        pre_sale_keywords = ['价格', '多少钱', '有货', '尺寸', '颜色', '款式', '推荐', '新款', '上市']
        post_sale_keywords = ['退货', '换货', '维修', '保修', '发票', '物流', '快递', '收到']

        # 投诉关键词分类
        # 强投诉词：明确的投诉行为
        strong_complaint_keywords = ['投诉', '差评', '举报', '315', '消费者协会', '工商', '找经理']
        # 不满情绪词：对产品/服务表达不满（核心投诉信号）
        dissatisfaction_keywords = [
            '太差', '质量差', '很差', '垃圾', '骗子', '骗人', '假的', '假货', '欺骗',
            '失望', '不满', '不满意', '太慢', '态度差', '服务差', '差的', '不好用',
            '质量太差', '质量不好', '做工差', '掉色', '褪色', '破损', '坏了', '有问题',
            '差劲', '太差了', '质量太差了', '差评', '给差评'
        ]
        # 功能性请求词（单独出现不算投诉，只是正常的售后需求）
        functional_keywords = ['退款', '退货', '换货', '催促', '发货', '收到货', '物流']

        all_text = ' '.join(messages).lower()

        positive_count = sum(1 for word in positive_words if word in all_text)
        negative_count = sum(1 for word in negative_words if word in all_text)

        pre_sale_count = sum(1 for word in pre_sale_keywords if word in all_text)
        post_sale_count = sum(1 for word in post_sale_keywords if word in all_text)

        # 投诉计数逻辑：
        # 1. 强投诉词出现1个 = 1次投诉（明确的投诉行为，如"我要投诉"）
        # 2. 不满情绪词出现1个 = 1次投诉（表达了对产品/服务的不满，如"质量太差了"）
        # 3. 但如果只有功能性请求词（退款/催发货），没有不满情绪词，不算投诉
        strong_matches = [kw for kw in strong_complaint_keywords if kw in all_text]
        dissatisfaction_matches = [kw for kw in dissatisfaction_keywords if kw in all_text]
        functional_matches = [kw for kw in functional_keywords if kw in all_text]

        complaint_count = 0
        if len(strong_matches) >= 1:
            # 强投诉词出现，直接算投诉（如"我要投诉"、"差评"）
            complaint_count = 1
        elif len(dissatisfaction_matches) >= 1:
            # 有不满情绪词，算投诉（如"质量太差了"、"垃圾产品"、"太失望了"）
            complaint_count = 1
        # 如果只有功能性请求词（退款/催发货），没有不满情绪，不算投诉
        # 例如："我要退款" 不算投诉，只是正常的售后请求
        # 例如："质量太差了，我要退款" 算投诉，因为有不满情绪词"太差"

        # Calculate sentiment score
        total_sentiment = positive_count + negative_count
        if total_sentiment > 0:
            sentiment_score = positive_count / total_sentiment
        else:
            sentiment_score = 0.5

        # Determine sentiment label
        if sentiment_score >= 0.6:
            sentiment_label = 'Positive'
        elif sentiment_score <= 0.4:
            sentiment_label = 'Negative'
        else:
            sentiment_label = 'Neutral'

        # Determine dominant intent
        intent_dist = {
            "Pre-sale Inquiry": pre_sale_count,
            "Post-sale Support": post_sale_count,
            "Logistics": 0,
            "Usage Guide": 0,
            "Complaint": complaint_count
        }

        if max(intent_dist.values()) > 0:
            dominant_intent = max(intent_dist.items(), key=lambda x: x[1])[0]
        else:
            dominant_intent = 'Unknown'

        # Calculate pre_sale_score and post_sale_score from intent_distribution
        intent_scores = TagCalculator.calculate_intent_scores(intent_dist)

        return {
            "buyer_nick": buyer_nick,
            "sentiment_score": round(sentiment_score, 2),
            "sentiment_label": sentiment_label,
            "intent_distribution": intent_dist,
            "dominant_intent": dominant_intent,
            "pre_sale_score": intent_scores['pre_sale_score'],
            "post_sale_score": intent_scores['post_sale_score'],
            "pre_sale_keywords": [],
            "post_sale_keywords": [],
            "complaint_count": complaint_count,
            "sentiment_method": "rule_based",
            "analyzed_at": datetime.now()
        }

    def _default_analysis(self, buyer_nick: str, reason: str) -> Dict[str, Any]:
        """Return default analysis when no data available"""
        return {
            "buyer_nick": buyer_nick,
            "sentiment_score": 0.5,
            "sentiment_label": "Neutral",
            "intent_distribution": {
                "Pre-sale Inquiry": 0,
                "Post-sale Support": 0,
                "Logistics": 0,
                "Usage Guide": 0,
                "Complaint": 0
            },
            "dominant_intent": "Unknown",
            "pre_sale_score": 0,
            "post_sale_score": 0,
            "pre_sale_keywords": [],
            "post_sale_keywords": [],
            "complaint_count": 0,
            "sentiment_method": f"default_{reason}",
            "analyzed_at": datetime.now()
        }

    def _extract_keywords(self, messages: List[str], keyword_type: str) -> List[str]:
        """Extract keywords from messages"""
        pre_sale_keywords = [
            '价格', '多少钱', '有货', '现货', '库存', '尺寸', '尺码', '颜色',
            '款式', '推荐', '新款', '上市', '还有吗', '链接', '双面', '材质',
            '面料', '羊绒', '骆驼绒', '标识', '徽标', 'ad标', '长尾标',
            '适合', '合身', '多大', '腰围', '胸围', '可以买吗', '怎么买'
        ]
        post_sale_keywords = [
            '退货', '退了', '退款', '退一下', '换货', '换成', '调换', '维修',
            '保修', '发票', '收到', '收到了', '售后', '售后服务', '裁袖',
            '裁一下', '修改', '改袖', '改裤脚', '签收', '寄到', '瑕疵',
            '划痕', '黑点', '小瑕疵', '包边', '带头', '不舒服', '不合适',
            '不想要', '发错', '少发', '漏发', '色差', '掉色', '褪色',
            '破损', '坏了', '有问题', '质量问题', '做工', '污渍'
        ]

        all_text = ' '.join(messages)

        if keyword_type == 'pre_sale':
            found = [kw for kw in pre_sale_keywords if kw in all_text]
        else:
            found = [kw for kw in post_sale_keywords if kw in all_text]

        return list(set(found))[:5]

    def save_analysis_result(self, result: Dict[str, Any], profile: Dict = None) -> bool:
        """
        Save analysis result to cache table

        使用 INSERT ... ON DUPLICATE KEY UPDATE 支持部分更新
        同时更新情感分析的独立数据快照与增量分析字段

        增量分析元数据由 process_buyer 计算后写入 result:
            incremental_chat_count, incremental_chat_from_date, incremental_chat_to_date,
            incremental_sentiment_label, incremental_sentiment_score, incremental_sentiment_analyzed_at

        sentiment_analyzed_last_chat_date 写入值 = incremental_chat_to_date
        （本次分析覆盖到的最早一条聊天时间；下次增量分析时作为起点）
        """
        from backend.database import Database
        from backend.config import settings

        try:
            db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
            db = Database(db_name=db_name)

            buyer_nick = result.get('buyer_nick')

            # 优先用增量分析的"覆盖到的时间"作为下次增量起点
            # 兜底用 profile 的最后聊天时间（兼容老调用方）
            last_chat = result.get('incremental_chat_to_date') or (
                profile.get('last_chat_date') if profile else None
            )

            # 使用新的表结构（情感分析独立字段 + 增量分析字段）
            query = """
                INSERT INTO buyer_ai_analysis_cache (
                    buyer_nick,
                    sentiment_score, sentiment_label, intent_distribution,
                    dominant_intent, pre_sale_keywords, post_sale_keywords,
                    complaint_count, sentiment_method,
                    sentiment_analyzed_at, sentiment_analyzed_last_chat_date,
                    incremental_chat_count, incremental_chat_from_date, incremental_chat_to_date,
                    incremental_sentiment_label, incremental_sentiment_score, incremental_sentiment_analyzed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    sentiment_score = VALUES(sentiment_score),
                    sentiment_label = VALUES(sentiment_label),
                    intent_distribution = VALUES(intent_distribution),
                    dominant_intent = VALUES(dominant_intent),
                    pre_sale_keywords = VALUES(pre_sale_keywords),
                    post_sale_keywords = VALUES(post_sale_keywords),
                    complaint_count = VALUES(complaint_count),
                    sentiment_method = VALUES(sentiment_method),
                    sentiment_analyzed_at = VALUES(sentiment_analyzed_at),
                    sentiment_analyzed_last_chat_date = VALUES(sentiment_analyzed_last_chat_date),
                    incremental_chat_count = VALUES(incremental_chat_count),
                    incremental_chat_from_date = VALUES(incremental_chat_from_date),
                    incremental_chat_to_date = VALUES(incremental_chat_to_date),
                    incremental_sentiment_label = VALUES(incremental_sentiment_label),
                    incremental_sentiment_score = VALUES(incremental_sentiment_score),
                    incremental_sentiment_analyzed_at = VALUES(incremental_sentiment_analyzed_at),
                    updated_at = CURRENT_TIMESTAMP
            """

            params = [
                buyer_nick,
                result.get('sentiment_score', 0.5),
                result.get('sentiment_label', 'Neutral'),
                json.dumps(result.get('intent_distribution', {}), ensure_ascii=False),
                result.get('dominant_intent', 'Unknown'),
                json.dumps(result.get('pre_sale_keywords', []), ensure_ascii=False),
                json.dumps(result.get('post_sale_keywords', []), ensure_ascii=False),
                result.get('complaint_count', 0),
                result.get('sentiment_method', 'unknown'),
                datetime.now(),
                last_chat,
                # 增量分析字段
                result.get('incremental_chat_count', 0),
                result.get('incremental_chat_from_date'),
                result.get('incremental_chat_to_date'),
                result.get('incremental_sentiment_label'),
                result.get('incremental_sentiment_score'),
                result.get('incremental_sentiment_analyzed_at'),
            ]

            db.execute_update(query, params)

            # Also update the main precomputed table with sentiment and intent scores
            update_query = """
                UPDATE target_buyers_precomputed
                SET
                    sentiment_label = %s,
                    sentiment_score = %s,
                    dominant_intent = %s,
                    pre_sale_score = %s,
                    post_sale_score = %s
                WHERE buyer_nick = %s
            """

            db.execute_update(update_query, [
                result.get('sentiment_label', 'Neutral'),
                result.get('sentiment_score', 0.5),
                result.get('dominant_intent', 'Unknown'),
                result.get('pre_sale_score', 0),
                result.get('post_sale_score', 0),
                buyer_nick
            ])

            logger.debug(f"[BatchAnalyzer] Saved analysis for {buyer_nick}")
            return True

        except Exception as e:
            logger.error(f"[BatchAnalyzer] Failed to save analysis for {result.get('buyer_nick')}: {e}")
            return False

    def start_batch_analysis(
        self,
        buyer_limit: int = 100,
        task_id: Optional[str] = None
    ) -> str:
        """Start a batch analysis task"""
        import uuid

        if task_id is None:
            task_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        task = BatchTask(
            task_id=task_id,
            status=BatchTaskStatus.PENDING,
            total_buyers=buyer_limit
        )

        with self.task_lock:
            self.tasks[task_id] = task

        # Start processing in background
        thread = threading.Thread(
            target=self._run_batch_analysis,
            args=(task_id, buyer_limit)
        )
        thread.daemon = True
        thread.start()

        logger.info(f"[BatchAnalyzer] Started batch task {task_id}")
        return task_id


    def _run_batch_analysis(self, task_id: str, buyer_limit: int):
        """Run the actual batch analysis (runs in background thread)"""
        from backend.ai.analyzer_orchestrator import get_analyzer_orchestrator

        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            task.status = BatchTaskStatus.RUNNING
            task.started_at = datetime.now()

        try:
            buyers = self.get_buyers_needing_analysis(buyer_limit)
            task.total_buyers = len(buyers)

            if not buyers:
                logger.info(f"[BatchAnalyzer] No buyers need analysis")
                task.status = BatchTaskStatus.COMPLETED
                task.completed_at = datetime.now()
                return

            orchestrator = get_analyzer_orchestrator()
            worker_count = max(2, min(self.max_workers, len(buyers)))

            def process_buyer(buyer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                if self._should_cancel(task_id):
                    return None

                try:
                    buyer_nick = buyer['buyer_nick']
                    # 增量模式：since_msg_time = cache.sentiment_analyzed_last_chat_date
                    # 首次分析（cache 还没有）since_msg_time 为 None，走全量路径
                    since = buyer.get('sentiment_analyzed_last_chat_date')
                    chats = self.get_buyer_chats(buyer_nick, limit=50, since_msg_time=since)
                    result = self.analyze_single_buyer(buyer_nick, chats, is_incremental=bool(since))

                    # 计算增量分析元数据，写入 cache.incremental_* 字段
                    if chats:
                        # chats 已按 msg_time DESC 排序；最末一条是最早的
                        result['incremental_chat_count'] = len(chats)
                        result['incremental_chat_from_date'] = since  # NULL for first-time
                        result['incremental_chat_to_date'] = chats[-1].get('msg_time')
                        # 首次分析时也填 incremental_sentiment_label（视为"首次增量"）
                        result['incremental_sentiment_label'] = result.get('sentiment_label', 'Neutral')
                        result['incremental_sentiment_score'] = result.get('sentiment_score', 0.5)
                        result['incremental_sentiment_analyzed_at'] = result.get('analyzed_at', datetime.now())
                    else:
                        # 没新聊天（不应发生，因 get_buyers_needing_analysis 不会触发）
                        result['incremental_chat_count'] = 0
                        result['incremental_chat_from_date'] = None
                        result['incremental_chat_to_date'] = None
                        result['incremental_sentiment_label'] = None
                        result['incremental_sentiment_score'] = None
                        result['incremental_sentiment_analyzed_at'] = None

                    self.save_analysis_result(result, profile=buyer)
                    return result
                except Exception as e:
                    logger.error(f"[BatchAnalyzer] Failed to process {buyer.get('buyer_nick')}: {e}")
                    return {"__error__": True, "buyer_nick": buyer.get('buyer_nick')}

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_map = {executor.submit(process_buyer, buyer): buyer for buyer in buyers}

                for future in as_completed(future_map):
                    if self._should_cancel(task_id):
                        self._mark_cancelled(task_id)
                        logger.info(f"[BatchAnalyzer] Batch task {task_id} cancelled during processing")
                        return

                    result = future.result()
                    if not result:
                        continue
                    if result.get("__error__"):
                        task.failed_buyers += 1
                        continue

                    task.results.append(result)
                    task.processed_buyers += 1
                    logger.debug(f"[BatchAnalyzer] Processed {result.get('buyer_nick')} ({task.processed_buyers}/{task.total_buyers})")

            task.status = BatchTaskStatus.COMPLETED
            task.completed_at = datetime.now()
            logger.info(f"[BatchAnalyzer] Batch task {task_id} completed: {task.processed_buyers} processed, {task.failed_buyers} failed")

        except Exception as e:
            logger.error(f"[BatchAnalyzer] Batch task {task_id} failed: {e}")
            task.status = BatchTaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a batch task"""
        with self.task_lock:
            task = self.tasks.get(task_id)

        if not task:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "total_buyers": task.total_buyers,
            "processed_buyers": task.processed_buyers,
            "skipped_buyers": task.skipped_buyers,
            "failed_buyers": task.failed_buyers,
            "progress_percent": round(task.processed_buyers / max(task.total_buyers, 1) * 100, 1),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat()
        }

    def cancel_batch_analysis(self, task_id: str) -> bool:
        """Cancel a running batch analysis task."""
        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            if task.status in {BatchTaskStatus.COMPLETED, BatchTaskStatus.FAILED, BatchTaskStatus.CANCELLED}:
                return False
            task.status = BatchTaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.error_message = "Cancelled by user"
            return True

    def _should_cancel(self, task_id: str) -> bool:
        with self.task_lock:
            task = self.tasks.get(task_id)
            return bool(task and task.status == BatchTaskStatus.CANCELLED)

    def _mark_cancelled(self, task_id: str):
        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            task.status = BatchTaskStatus.CANCELLED
            task.completed_at = datetime.now()
            if not task.error_message:
                task.error_message = "Cancelled by user"

    def get_sentiment_summary(self) -> Dict[str, Any]:
        """Get overall sentiment distribution summary

        更新: 2026-03-19 优先使用缓存表实时数据
        """
        from backend.database import Database
        from backend.config import settings

        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        query = """
            SELECT
                COALESCE(cache.sentiment_label, tb.sentiment_label) AS sentiment_label,
                COUNT(*) as count,
                AVG(COALESCE(cache.sentiment_score, tb.sentiment_score)) as avg_score
            FROM target_buyers_precomputed tb
            LEFT JOIN buyer_ai_analysis_cache cache ON tb.buyer_nick = cache.buyer_nick
            WHERE COALESCE(cache.sentiment_label, tb.sentiment_label) IS NOT NULL
            GROUP BY COALESCE(cache.sentiment_label, tb.sentiment_label)
        """

        results = db.execute_query(query)

        summary = {
            "total_analyzed": 0,
            "positive": {"count": 0, "avg_score": 0},
            "neutral": {"count": 0, "avg_score": 0.5},
            "negative": {"count": 0, "avg_score": 0}
        }

        for row in results:
            label = row.get('sentiment_label', '').lower()
            count = row.get('count', 0)
            avg_score = row.get('avg_score', 0.5)

            summary["total_analyzed"] += count

            if label == 'positive':
                summary["positive"] = {"count": count, "avg_score": round(float(avg_score), 2)}
            elif label == 'negative':
                summary["negative"] = {"count": count, "avg_score": round(float(avg_score), 2)}
            elif label == 'neutral':
                summary["neutral"] = {"count": count, "avg_score": round(float(avg_score), 2)}

        return summary

    def get_intent_summary(self) -> Dict[str, Any]:
        """Get overall intent distribution summary

        更新: 2026-03-19 优先使用缓存表实时数据
        """
        from backend.database import Database
        from backend.config import settings

        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        query = """
            SELECT
                COALESCE(cache.dominant_intent, tb.dominant_intent) AS dominant_intent,
                COUNT(*) as count
            FROM target_buyers_precomputed tb
            LEFT JOIN buyer_ai_analysis_cache cache ON tb.buyer_nick = cache.buyer_nick
            WHERE COALESCE(cache.dominant_intent, tb.dominant_intent) IS NOT NULL
            GROUP BY COALESCE(cache.dominant_intent, tb.dominant_intent)
            ORDER BY count DESC
        """

        results = db.execute_query(query)

        summary = {
            "total_analyzed": 0,
            "intents": {}
        }

        for row in results:
            intent = row.get('dominant_intent', 'Unknown')
            count = row.get('count', 0)

            summary["total_analyzed"] += count
            summary["intents"][intent] = count

        return summary

    def force_refresh(self, buyer_nick: str):
        """强制刷新情感缓存"""
        from backend.database import Database
        from backend.config import settings

        try:
            db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
            db = Database(db_name=db_name)

            sql = """
                UPDATE buyer_ai_analysis_cache
                SET sentiment_score = NULL,
                    sentiment_label = NULL,
                    intent_distribution = NULL,
                    dominant_intent = NULL,
                    pre_sale_keywords = NULL,
                    post_sale_keywords = NULL,
                    complaint_count = 0,
                    sentiment_method = NULL
                WHERE buyer_nick = %s
            """
            db.execute_update(sql, (buyer_nick,))
            logger.info(f"[BatchAnalyzer] 已清除情感缓存: {buyer_nick}")
        except Exception as e:
            logger.error(f"[BatchAnalyzer] 清除情感缓存失败: {e}")


# Singleton instance
_batch_analyzer_instance = None
_batch_analyzer_lock = threading.Lock()


def get_batch_analyzer() -> BatchAnalyzer:
    """Get singleton BatchAnalyzer instance"""
    global _batch_analyzer_instance

    if _batch_analyzer_instance is None:
        with _batch_analyzer_lock:
            if _batch_analyzer_instance is None:
                _batch_analyzer_instance = BatchAnalyzer()

    return _batch_analyzer_instance
