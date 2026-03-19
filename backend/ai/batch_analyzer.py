"""
Batch Analyzer - 批量AI情绪/意图分析

缓存策略: 纯增量更新，无TTL
- 存储数据快照 (analyzed_last_purchase_date, analyzed_last_chat_date)
- 只有新聊天才触发重新分析
- 前提条件: 聊天天数 >= 10

功能:
1. 增量更新: 只分析有新增聊天记录的客户
2. 智能限流: 每分钟最多20次API调用
3. 多级降级: 智谱GLM-4.7 → DeepSeek → 规则引擎
4. 批量处理: 每批20个客户
"""
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading

from backend.analytics.tag_calculator import TagCalculator

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
            from backend.ai.zhipu_client import ZhipuClient
            self.zhipu_client = ZhipuClient()
            logger.info("[BatchAnalyzer] ZhipuClient initialized")
        except Exception as e:
            logger.warning(f"[BatchAnalyzer] Failed to init ZhipuClient: {e}")
            self.zhipu_client = None

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

    def get_buyer_chats(self, buyer_nick: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent chat messages for a buyer"""
        from backend.database import Database, BuyerQueries
        from backend.config import settings

        db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
        db = Database(db_name=db_name)

        query, params = BuyerQueries.get_chat_messages(buyer_nick, limit)
        return db.execute_query(query, params)

    def analyze_single_buyer(
        self,
        buyer_nick: str,
        chats: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze sentiment and intent for a single buyer

        Uses multi-level fallback:
        1. Zhipu GLM-4.7 (preferred - monthly subscription)
        2. DeepSeek-Chat (fallback - pay per token)
        3. Rule-based (final fallback)

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
                "sentiment_method": str
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

        result = {
            "buyer_nick": buyer_nick,
            "analyzed_at": datetime.now()
        }

        # Try Zhipu first (preferred)
        if self.zhipu_client:
            try:
                self.rate_limiter.wait()
                logger.debug(f"[BatchAnalyzer] Analyzing {buyer_nick} with Zhipu")

                # Sentiment analysis
                sentiment_results = self.zhipu_client.analyze_sentiment_batch(buyer_messages[:20])

                # Check if all results are neutral (indicates API fallback)
                all_neutral = all(r.get('sentiment') == 'Neutral' and r.get('score') == 0.5 for r in sentiment_results)

                if all_neutral:
                    logger.info(f"[BatchAnalyzer] Zhipu returned defaults for {buyer_nick}, falling through to DeepSeek")
                    raise Exception("Zhipu returned default values, trying DeepSeek fallback")

                # Calculate average sentiment
                if sentiment_results:
                    avg_score = sum(r.get('score', 0.5) for r in sentiment_results) / len(sentiment_results)
                    sentiment_labels = [r.get('sentiment', 'Neutral') for r in sentiment_results]

                    # Determine overall label
                    positive_count = sentiment_labels.count('Positive')
                    negative_count = sentiment_labels.count('Negative')

                    if positive_count > negative_count and positive_count > len(sentiment_labels) / 2:
                        overall_label = 'Positive'
                    elif negative_count > positive_count and negative_count > len(sentiment_labels) / 2:
                        overall_label = 'Negative'
                    else:
                        overall_label = 'Neutral'

                    result['sentiment_score'] = round(avg_score, 2)
                    result['sentiment_label'] = overall_label

                # Intent analysis
                self.rate_limiter.wait()
                intent_dist = self.zhipu_client.extract_intent_distribution(buyer_messages)

                # Check if intent distribution is all zeros (indicates API fallback)
                if all(v == 0 for v in intent_dist.values()):
                    logger.info(f"[BatchAnalyzer] Zhipu intent failed for {buyer_nick}, falling through to DeepSeek")
                    raise Exception("Zhipu intent analysis failed, trying DeepSeek fallback")

                result['intent_distribution'] = intent_dist

                # Determine dominant intent
                if intent_dist:
                    result['dominant_intent'] = max(intent_dist.items(), key=lambda x: x[1])[0]
                else:
                    result['dominant_intent'] = 'Unknown'

                result['sentiment_method'] = 'zhipu_glm4'
                result['complaint_count'] = intent_dist.get('Complaint', 0)

                # Calculate pre_sale_score and post_sale_score from intent_distribution
                intent_scores = TagCalculator.calculate_intent_scores(intent_dist)
                result['pre_sale_score'] = intent_scores['pre_sale_score']
                result['post_sale_score'] = intent_scores['post_sale_score']

                # Extract keywords
                result['pre_sale_keywords'] = self._extract_keywords(buyer_messages, 'pre_sale')
                result['post_sale_keywords'] = self._extract_keywords(buyer_messages, 'post_sale')

                return result

            except Exception as e:
                logger.warning(f"[BatchAnalyzer] Zhipu failed for {buyer_nick}: {e}")

        # Fallback to DeepSeek
        if self.deepseek_client:
            try:
                self.rate_limiter.wait()
                logger.info(f"[BatchAnalyzer] Analyzing {buyer_nick} with DeepSeek (fallback)")

                # 使用DeepSeek进行情感分析
                deepseek_result = self.deepseek_client.analyze_sentiment_intent(
                    buyer_nick,
                    buyer_messages[:20]
                )

                result['sentiment_score'] = deepseek_result.get('sentiment_score', 0.5)
                result['sentiment_label'] = deepseek_result.get('sentiment_label', 'Neutral')
                result['intent_distribution'] = deepseek_result.get('intent_distribution', {})
                result['dominant_intent'] = deepseek_result.get('dominant_intent', 'Unknown')
                result['complaint_count'] = deepseek_result.get('complaint_count', 0)
                result['sentiment_method'] = 'deepseek'

                # Calculate pre_sale_score and post_sale_score from intent_distribution
                intent_scores = TagCalculator.calculate_intent_scores(result['intent_distribution'])
                result['pre_sale_score'] = intent_scores['pre_sale_score']
                result['post_sale_score'] = intent_scores['post_sale_score']

                # Extract keywords
                result['pre_sale_keywords'] = self._extract_keywords(buyer_messages, 'pre_sale')
                result['post_sale_keywords'] = self._extract_keywords(buyer_messages, 'post_sale')

                logger.info(f"[BatchAnalyzer] DeepSeek analysis completed for {buyer_nick}")
                return result

            except Exception as e:
                logger.warning(f"[BatchAnalyzer] DeepSeek failed for {buyer_nick}: {e}")

        # Final fallback to rule-based
        return self._rule_based_analysis(buyer_nick, buyer_messages)

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
        pre_sale_keywords = ['价格', '多少钱', '有货', '尺寸', '颜色', '款式', '推荐']
        post_sale_keywords = ['退货', '换货', '维修', '保修', '发票']

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
        同时更新情感分析的独立数据快照
        """
        from backend.database import Database
        from backend.config import settings

        try:
            db_name = settings.db_name_to_use if settings.db_name_to_use else 'aliyunDB'
            db = Database(db_name=db_name)

            buyer_nick = result.get('buyer_nick')

            # 获取数据快照（情感分析只关心聊天时间）
            last_chat = profile.get('last_chat_date') if profile else None

            # 使用新的表结构（情感分析独立字段）
            query = """
                INSERT INTO buyer_ai_analysis_cache (
                    buyer_nick,
                    sentiment_score, sentiment_label, intent_distribution,
                    dominant_intent, pre_sale_keywords, post_sale_keywords,
                    complaint_count, sentiment_method,
                    sentiment_analyzed_at, sentiment_analyzed_last_chat_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                last_chat
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
        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            task.status = BatchTaskStatus.RUNNING
            task.started_at = datetime.now()

        try:
            # Get buyers needing analysis
            buyers = self.get_buyers_needing_analysis(buyer_limit)
            task.total_buyers = len(buyers)

            if not buyers:
                logger.info(f"[BatchAnalyzer] No buyers need analysis")
                task.status = BatchTaskStatus.COMPLETED
                task.completed_at = datetime.now()
                return

            # Process in batches
            for i in range(0, len(buyers), self.batch_size):
                batch = buyers[i:i + self.batch_size]

                for buyer in batch:
                    try:
                        buyer_nick = buyer['buyer_nick']

                        # Get chats
                        chats = self.get_buyer_chats(buyer_nick, limit=50)

                        # Analyze
                        result = self.analyze_single_buyer(buyer_nick, chats)

                        # Save result with profile for data snapshot
                        self.save_analysis_result(result, profile=buyer)

                        task.results.append(result)
                        task.processed_buyers += 1

                        logger.debug(f"[BatchAnalyzer] Processed {buyer_nick} ({task.processed_buyers}/{task.total_buyers})")

                    except Exception as e:
                        logger.error(f"[BatchAnalyzer] Failed to process {buyer.get('buyer_nick')}: {e}")
                        task.failed_buyers += 1

                # Small delay between batches
                time.sleep(1)

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
