# AI分析系统优化计划

> **注意**: 本文档为优化计划，部分功能已实现。已完成的优化详见 [2026-02-24-ai-optimization-summary.md](./2026-02-24-ai-optimization-summary.md)

## 📋 项目概述

**目标**: 优化AI客户分析系统的性能、成本和用户体验

**当前状态**:
- ✅ DeepSeek-R1分析正常工作（有聊天记录的客户）
- ✅ Zhipu GLM-4.7分析正常工作（无聊天记录的客户）
- ✅ 多级降级策略已实现（DeepSeek → GLM-4.7 → 规则引擎）
- ✅ MySQL缓存机制已实现
- ✅ 429错误自动降级已实现
- ✅ 画像质量满足基本需求
- ⚠️ 首次响应时间：60-90秒（缓存命中 < 0.1秒）
- ⚠️ 异步处理待实现
- ⚠️ 成本监控待完善

**优化方向**:
1. ✅ 缓存机制 - 最大化复用，减少API调用
2. ✅ 智能降级策略 - 基于成本优化选择模型
3. ⏳ 异步处理 - 提升用户体验
4. ⏳ 成本监控 - 实时追踪和控制
5. ⏳ Prompt优化 - 提升分析质量

---

## Phase 1: 缓存机制实现 ⚡ (最高优先级)

### 目标
将重复查询的响应时间从72秒降到<0.1秒，降低API成本60-80%

### 1.1 Redis缓存实现

**文件**: `backend/ai/cache_manager.py`

```python
"""
AI分析结果缓存管理器
使用Redis实现高性能缓存
"""
import json
import hashlib
from datetime import timedelta
from typing import Dict, Optional
import redis

from backend.config import settings


class AICacheManager:
    """AI分析缓存管理器"""

    def __init__(self):
        """初始化Redis连接"""
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )

    def get_cache_key(self, buyer_nick: str, profile: Dict) -> str:
        """
        生成缓存键

        包含客户关键属性，确保数据变化时失效
        """
        key_data = {
            "buyer_nick": buyer_nick,
            "vip_level": profile.get("vip_level", ""),
            "l6m_netsales": profile.get("l6m_netsales", 0),
            "last_purchase_date": profile.get("last_purchase_date", ""),
            "chat_count": profile.get("chat_count", 0)
        }
        data_str = json.dumps(key_data, sort_keys=True)
        hash_key = hashlib.md5(data_str.encode()).hexdigest()
        return f"ai_analysis:{buyer_nick}:{hash_key}"

    def get(self, buyer_nick: str, profile: Dict) -> Optional[Dict]:
        """获取缓存的分析结果"""
        cache_key = self.get_cache_key(buyer_nick, profile)
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"[Cache] Get failed: {e}")
        return None

    def set(self, buyer_nick: str, profile: Dict, result: Dict, ttl_days: int = 30):
        """
        设置缓存

        Args:
            buyer_nick: 客户昵称
            profile: 客户档案
            result: AI分析结果
            ttl_days: 缓存过期天数（默认30天）
        """
        cache_key = self.get_cache_key(buyer_nick, profile)
        ttl_seconds = ttl_days * 24 * 3600

        try:
            self.redis_client.setex(
                cache_key,
                ttl_seconds,
                json.dumps(result, ensure_ascii=False)
            )
            print(f"[Cache] Cached {buyer_nick} for {ttl_days} days")
        except Exception as e:
            print(f"[Cache] Set failed: {e}")

    def delete(self, buyer_nick: str):
        """删除客户的所有缓存（数据更新时调用）"""
        pattern = f"ai_analysis:{buyer_nick}:*"
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                print(f"[Cache] Deleted {len(keys)} cache entries for {buyer_nick}")
        except Exception as e:
            print(f"[Cache] Delete failed: {e}")

    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        try:
            all_keys = self.redis_client.keys("ai_analysis:*")
            total_cached = len(all_keys)

            # 计算总内存使用
            info = self.redis_client.info("memory")
            used_memory_mb = info.get("used_memory", 0) / (1024 * 1024)

            return {
                "total_cached": total_cached,
                "used_memory_mb": round(used_memory_mb, 2),
                "avg_size_kb": round((used_memory_mb * 1024) / total_cached, 2) if total_cached > 0 else 0
            }
        except Exception as e:
            print(f"[Cache] Stats failed: {e}")
            return {"error": str(e)}
```

**配置更新**: `backend/config/settings.py`

```python
class Settings(BaseSettings):
    # ... 现有配置 ...

    # Redis配置
    redis_host: str = Field(default="localhost", description="Redis主机")
    redis_port: int = Field(default=6379, description="Redis端口")
    redis_db: int = Field(default=0, description="Redis数据库")
    redis_password: Optional[str] = Field(default=None, description="Redis密码")

    # AI缓存配置
    ai_enable_cache: bool = Field(default=True, description="启用AI缓存")
    ai_cache_ttl_days: int = Field(default=30, description="缓存TTL（天）")

    class Config:
        extra = "ignore"
```

### 1.2 分层缓存策略

**文件**: `backend/ai/cache_strategy.py`

```python
"""
分层缓存策略
根据客户价值和行为特征，动态调整缓存时间
"""
from enum import Enum


class CacheTier(Enum):
    """缓存层级"""
    HOT = 7          # 热数据：7天（VIP，高价值客户）
    WARM = 14        # 温数据：14天（有聊天记录）
    COLD = 30        # 冷数据：30天（无聊天记录）


def get_cache_tier(profile: Dict, chats_count: int) -> CacheTier:
    """
    根据客户特征确定缓存层级

    策略：
    - V3/V2客户：HOT（7天，数据变化快）
    - 有聊天记录：WARM（14天，行为可能变化）
    - 无聊天记录：COLD（30天，主要看消费历史）
    """
    vip_level = profile.get("vip_level", "Non-VIP")

    # VIP客户（高价值，数据变化快）
    if vip_level in ["V3", "V2"]:
        return CacheTier.HOT

    # 有聊天记录（行为可能变化）
    if chats_count > 0:
        return CacheTier.WARM

    # 无聊天记录（仅消费数据，稳定）
    return CacheTier.COLD


def get_cache_ttl(tier: CacheTier) -> int:
    """获取缓存TTL（天数）"""
    return tier.value
```

### 1.3 集成到Orchestrator

**文件**: `backend/ai/analyzer_orchestrator.py`

```python
from backend.ai.cache_manager import AICacheManager
from backend.ai.cache_strategy import get_cache_tier, get_cache_ttl


class AnalyzerOrchestrator:
    """分析器编排器"""

    def __init__(self):
        # ... 现有代码 ...
        self.cache_manager = AICacheManager() if settings.ai_enable_cache else None

    def analyze_buyer_persona(self, buyer_nick: str, profile: Dict, chats: List[Dict], orders: List[Dict]) -> Dict:
        """多级降级分析策略（带缓存）"""

        # 检查缓存
        if self.cache_manager:
            cached = self.cache_manager.get(buyer_nick, profile)
            if cached:
                print(f"[Orchestrator] 缓存命中: {buyer_nick}")
                return cached

        # ... 执行AI分析（现有逻辑） ...

        result = self._perform_analysis(buyer_nick, profile, chats, orders)

        # 缓存结果
        if self.cache_manager and result:
            cache_tier = get_cache_tier(profile, len(chats))
            ttl_days = get_cache_ttl(cache_tier)

            self.cache_manager.set(
                buyer_nick,
                profile,
                result,
                ttl_days=ttl_days
            )

        return result
```

### 1.4 缓存失效机制

**API端点**: `backend/api/target_routes.py`

```python
@router.post("/buyers/{user_nick}/invalidate-cache")
async def invalidate_buyer_cache(user_nick: str):
    """
    使客户缓存失效（数据更新时调用）

    使用场景：
    - 客户新下单
    - 客户有新聊天记录
    - 手动刷新分析
    """
    try:
        from backend.ai.cache_manager import AICacheManager
        cache_mgr = AICacheManager()

        # 获取客户profile
        profile = analyzer.get_buyer_profile(user_nick)
        if profile:
            cache_mgr.delete(user_nick)
            return {"status": "success", "message": f"已清除 {user_nick} 的缓存"}
        else:
            raise HTTPException(status_code=404, detail=f"客户 {user_nick} 不存在")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 预期收益

| 指标 | 当前 | 优化后 | 提升 |
|------|------|--------|------|
| 首次查询响应 | 72秒 | 72秒 | - |
| 缓存命中响应 | 72秒 | <0.1秒 | **720x** |
| 月度API调用 | 3000次 | 600次 | **80%↓** |
| 月度DeepSeek成本 | ¥21,000 | ¥4,200 | **80%↓** |

---

## Phase 2: 智能降级策略优化 🎯 (核心优化)

### 目标
基于成本优化，合理选择AI模型，降低DeepSeek成本90%

### 2.1 成本模型

**当前定价**:
- **Zhipu GLM-4**: 月卡，不限token使用量 → **优先使用**
- **DeepSeek-R1**: ¥1/百万tokens（输入），¥2/百万tokens（输出） → 约¥7/次
- **DeepSeek-Chat**: ¥1/百万tokens → 约¥3/次

**单次成本估算**:
- DeepSeek-R1: 7000 tokens × ¥0.001 = **¥7/次**
- DeepSeek-Chat: 3000 tokens × ¥0.001 = **¥3/次**
- Zhipu: **¥0/次**（月卡）

### 2.2 智能模型选择策略

**文件**: `backend/ai/model_selection.py`

```python
"""
智能模型选择策略
基于成本优化，合理分配AI模型
"""
from typing import Literal


ModelType = Literal["deepseek-r1", "deepseek-chat", "zhipu", "rule-based"]


def select_ai_model(
    chats_count: int,
    is_vic: bool,
    vip_level: str
) -> ModelType:
    """
    智能选择AI模型

    策略：
    1. 无聊天 → Zhipu（月卡，不需要文本分析）
    2. 聊天少(<10) → Zhipu（月卡，文本少没必要用DeepSeek）
    3. 聊天中(10-20) → DeepSeek-Chat（省钱，够用）
    4. 聊天多(>20) → DeepSeek-R1（深度分析值得）
    5. VIC客户 → 优待DeepSeek-R1

    Args:
        chats_count: 聊天记录条数
        is_vic: 是否VIC客户
        vip_level: VIP等级

    Returns:
        选择的模型类型
    """
    # 特殊优待：VIC客户 + 有聊天 → DeepSeek-R1
    if is_vic and chats_count > 0:
        print(f"[Model-Selection] VIC客户优待 → DeepSeek-R1")
        return "deepseek-r1"

    # 无聊天记录 → Zhipu（月卡，随便用）
    if chats_count == 0:
        print(f"[Model-Selection] 无聊天 → Zhipu (月卡)")
        return "zhipu"

    # 聊天条数少（<10条）→ Zhipu
    if chats_count < 10:
        print(f"[Model-Selection] 聊天少({chats_count}条) → Zhipu (月卡够用)")
        return "zhipu"

    # 聊天中等（10-20条）→ DeepSeek-Chat
    if 10 <= chats_count <= 20:
        print(f"[Model-Selection] 聊天中({chats_count}条) → DeepSeek-Chat (性价比)")
        return "deepseek-chat"

    # 聊天多（>20条）→ DeepSeek-R1
    if chats_count > 20:
        print(f"[Model-Selection] 聊天多({chats_count}条) → DeepSeek-R1 (深度分析)")
        return "deepseek-r1"

    # 默认：Zhipu
    return "zhipu"


def estimate_cost(model: ModelType) -> float:
    """估算单次分析成本（元）"""
    costs = {
        "deepseek-r1": 7.0,
        "deepseek-chat": 3.0,
        "zhipu": 0.0,
        "rule-based": 0.0
    }
    return costs.get(model, 0.0)
```

### 2.3 Orchestrator实现（优化版）

**文件**: `backend/ai/analyzer_orchestrator.py`

```python
def analyze_buyer_persona(
    self,
    buyer_nick: str,
    profile: Dict,
    chats: List[Dict],
    orders: List[Dict]
) -> Dict[str, Any]:
    """
    优化后的多级降级分析策略（基于成本优化）

    新策略：
    - 无聊天 → Zhipu（月卡）
    - 聊天少(<10) → Zhipu（月卡）
    - 聊天中(10-20) → DeepSeek-Chat（省钱）
    - 聊天多(>20) → DeepSeek-R1（深度分析）
    - VIC客户 → 优待DeepSeek-R1
    """
    # 检查缓存
    if self.cache_manager:
        cached = self.cache_manager.get(buyer_nick, profile)
        if cached:
            print(f"[Orchestrator] ✓ 缓存命中: {buyer_nick}")
            return cached

    # 提取关键信息
    has_chats = chats and len(chats) > 0
    chat_count = len(chats) if has_chats else 0
    is_vic = profile.get("is_vic", 0) == 1
    vip_level = profile.get("vip_level", "Non-VIP")

    print(f"[Orchestrator] 分析 {buyer_nick}")
    print(f"  - 聊天记录: {chat_count}条")
    print(f"  - VIP等级: {vip_level}")
    print(f"  - 是否VIC: {is_vic}")

    # 智能选择模型
    model_type = select_ai_model(chat_count, is_vic, vip_level)

    result = None

    # 执行分析（根据选择的模型）
    if model_type == "deepseek-r1" and self.deepseek:
        try:
            print(f"[DeepSeek-R1] 深度推理分析...")
            result = self.deepseek.analyze_buyer_persona(
                buyer_nick, profile, chats, orders
            )
            result["analysis_method"] = "DeepSeek-R1"
            result["data_source"] = "聊天记录+消费数据(深度分析)"
            result["estimated_cost"] = estimate_cost("deepseek-r1")

        except Exception as e:
            print(f"[降级] DeepSeek-R1失败: {e} → 尝试DeepSeek-Chat")
            model_type = "deepseek-chat"

    if model_type == "deepseek-chat" and self.deepseek and result is None:
        try:
            print(f"[DeepSeek-Chat] 快速分析...")
            result = self.deepseek.analyze_buyer_persona_chat(
                buyer_nick, profile, chats, orders
            )
            result["analysis_method"] = "DeepSeek-Chat"
            result["data_source"] = "聊天记录+消费数据(快速分析)"
            result["estimated_cost"] = estimate_cost("deepseek-chat")

        except Exception as e:
            print(f"[降级] DeepSeek-Chat失败: {e} → 尝试Zhipu")
            model_type = "zhipu"

    if model_type == "zhipu" and self.zhipu and result is None:
        try:
            print(f"[Zhipu-GLM] 分析（月卡）...")
            result = self.zhipu.analyze_buyer_persona(
                buyer_nick, profile, chats,
                self._format_order_summary(orders)
            )
            result["analysis_method"] = "Zhipu-GLM"
            result["data_source"] = "聊天记录+消费数据(月卡)" if has_chats else "消费数据(月卡)"
            result["estimated_cost"] = estimate_cost("zhipu")

        except Exception as e:
            print(f"[降级] Zhipu失败: {e} → 使用规则引擎")

    # 最终兜底：规则引擎
    if result is None:
        print(f"[规则引擎] 所有AI模型失败，使用规则分析")
        result = self.rule_based.analyze(profile, chats, orders)
        result["analysis_method"] = "Rule-Based"
        result["data_source"] = "规则引擎(兜底)"
        result["estimated_cost"] = 0.0

    # 缓存结果
    if self.cache_manager:
        cache_tier = get_cache_tier(profile, chat_count)
        ttl_days = get_cache_ttl(cache_tier)
        self.cache_manager.set(buyer_nick, profile, result, ttl_days=ttl_days)

    # 记录成本
    self._track_cost(buyer_nick, result)

    return result


def _track_cost(self, buyer_nick: str, result: Dict):
    """追踪分析成本"""
    cost = result.get("estimated_cost", 0.0)
    method = result.get("analysis_method", "Unknown")
    print(f"[成本追踪] {buyer_nick} - {method}: ¥{cost}")
```

### 2.4 DeepSeek-Chat接口实现

**文件**: `backend/ai/deepseek_client.py`

```python
def analyze_buyer_persona_chat(
    self,
    buyer_nick: str,
    profile: Dict,
    chats: List[Dict],
    orders: List[Dict]
) -> Dict[str, Any]:
    """
    使用DeepSeek-Chat（非R1推理版）进行快速分析

    与R1版本的区别：
    - 不使用两阶段推理
    - 单次API调用，速度快（20-30秒 vs 60-90秒）
    - Token消耗少（~3000 vs ~7000）
    - 成本低（¥3 vs ¥7）

    适用场景：
    - 聊天记录中等（10-20条）
    - 不需要深度推理，快速分析够用
    """
    try:
        # 1. 提取行为特征
        behavior = BehaviorAnalyzer.extract_behavior_from_data(
            profile, chats, orders
        )

        # 2. 构建单轮分析prompt（不需要推理链）
        prompt = self._build_chat_prompt(buyer_nick, profile, behavior)

        # 3. 调用DeepSeek-Chat API
        response = self.client.chat.completions.create(
            model="deepseek-chat",  # 非reasoning模型
            messages=[
                {
                    "role": "system",
                    "content": "你是一位资深的电商客户分析专家，擅长从订单数据和聊天记录中分析买家的购买行为、偏好和需求。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # 不需要高温度，直接分析
            max_tokens=2000
        )

        # 4. 解析响应
        response_text = response.choices[0].message.content

        # 5. 记录token使用
        usage = response.usage
        print(f"[DeepSeek-Chat] Token使用: {usage.total_tokens} (输入: {usage.prompt_tokens}, 输出: {usage.completion_tokens})")

        return self._parse_ai_response(response_text)

    except Exception as e:
        print(f"[DeepSeek-Chat] 分析失败: {e}")
        raise


def _build_chat_prompt(self, buyer_nick: str, profile: Dict, behavior: Dict) -> str:
    """构建DeepSeek-Chat的prompt（单轮，简化版）"""

    # 提取关键信息
    vip_level = profile.get("vip_level", "Non-VIP")
    l6m_netsales = profile.get("l6m_netsales", 0)
    total_orders = profile.get("total_orders", 0)
    refund_rate = profile.get("refund_rate", 0)

    # 聊天内容摘要
    chat_summary = behavior.get("communication_style", "")

    # 消费行为摘要
    consumption_summary = behavior.get("consumption_pattern", "")

    prompt = f"""
请分析以下客户的购买行为和偏好：

**客户信息**：
- 客户昵称：{buyer_nick}
- VIP等级：{vip_level}
- 近6个月销售额：¥{l6m_netsales:,.2f}
- 历史订单数：{total_orders}
- 退款率：{refund_rate*100:.1f}%

**沟通风格**：
{chat_summary}

**消费行为**：
{consumption_summary}

**要求**：
1. 用2-3句话总结客户画像
2. 列出3-5个关键兴趣点
3. 列出2-3个痛点或需求
4. 给出具体的销售建议

请以JSON格式返回：
{{
    "summary": "客户画像总结",
    "key_interests": ["兴趣1", "兴趣2", ...],
    "pain_points": ["痛点1", "痛点2", ...],
    "recommended_action": "具体销售建议"
}}
"""
    return prompt
```

### 2.5 成本优化效果预测

**场景分析**（假设100个客户/天）：

| 场景 | 占比 | 聊天数 | 当前模型 | 优化模型 | 成本/次 | 日成本 | 月成本 |
|------|------|--------|----------|----------|--------|--------|--------|
| 无聊天 | 40% | 0 | DeepSeek-R1 | **Zhipu** | ¥7→¥0 | ¥0→¥0 | **¥0** |
| 聊天少 | 30% | <10 | DeepSeek-R1 | **Zhipu** | ¥7→¥0 | ¥0→¥0 | **¥0** |
| 聊天中 | 20% | 10-20 | DeepSeek-R1 | **DeepSeek-Chat** | ¥7→¥3 | ¥40→¥60 | ¥1,200 |
| 聊天多 | 10% | >20 | DeepSeek-R1 | DeepSeek-R1 | ¥7 | ¥70 | ¥2,100 |
| **总计** | 100% | - | - | - | - | **¥110** | **¥3,300** |

**对比优化前**:
- 优化前：100% DeepSeek-R1 = 100次 × ¥7 = ¥700/天 = **¥21,000/月**
- 优化后：混合策略 = ¥110/天 = **¥3,300/月**
- **节省**: ¥590/天 = **¥17,700/月 (84%↓)** 💰

**缓存命中后**:
- 假设缓存命中率70%
- 实际API调用：30次/天
- 实际成本：¥33/天 = **¥990/月**
- **总节省**: ¥667/天 = **¥20,010/月 (95%↓)** 🎉

---

## Phase 3: 异步处理 + 轮询机制 🔄

### 目标
提升用户体验，点击"AI分析"后立即返回，后台异步处理

### 3.1 异步任务队列

**文件**: `backend/ai/task_queue.py`

```python
"""
异步任务管理
使用内存队列（简单实现），生产环境可用Celery + Redis
"""
import asyncio
from datetime import datetime
from typing import Dict, Optional
import uuid


class AITaskManager:
    """AI分析任务管理器"""

    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.max_concurrent = 5  # 最多同时5个任务
        self.running_tasks = 0

    def create_task(
        self,
        buyer_nick: str,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ) -> str:
        """创建异步分析任务"""
        task_id = str(uuid.uuid4())

        self.tasks[task_id] = {
            "task_id": task_id,
            "buyer_nick": buyer_nick,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "result": None,
            "error": None
        }

        # 启动异步任务
        asyncio.create_task(self._execute_task(task_id, profile, chats, orders))

        return task_id

    async def _execute_task(
        self,
        task_id: str,
        profile: Dict,
        chats: List[Dict],
        orders: List[Dict]
    ):
        """执行分析任务（后台）"""
        # 等待并发控制
        while self.running_tasks >= self.max_concurrent:
            await asyncio.sleep(1)

        self.running_tasks += 1
        self.tasks[task_id]["status"] = "processing"

        try:
            # 执行分析
            from backend.ai.analyzer_orchestrator import get_analyzer_orchestrator
            orchestrator = get_analyzer_orchestrator()

            result = orchestrator.analyze_buyer_persona(
                self.tasks[task_id]["buyer_nick"],
                profile,
                chats,
                orders
            )

            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["result"] = result
            self.tasks[task_id]["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["error"] = str(e)

        finally:
            self.running_tasks -= 1

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.tasks.get(task_id)

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        to_delete = []
        for task_id, task in self.tasks.items():
            created_at = datetime.fromisoformat(task["created_at"])
            if created_at < cutoff and task["status"] in ["completed", "failed"]:
                to_delete.append(task_id)

        for task_id in to_delete:
            del self.tasks[task_id]

        print(f"[TaskManager] 清理了 {len(to_delete)} 个旧任务")


# 全局单例
_task_manager_instance = None


def get_task_manager() -> AITaskManager:
    """获取任务管理器单例"""
    global _task_manager_instance
    if _task_manager_instance is None:
        _task_manager_instance = AITaskManager()
    return _task_manager_instance
```

### 3.2 异步API端点

**文件**: `backend/api/target_routes.py`

```python
@router.post("/buyers/{user_nick}/analyze-async")
async def analyze_buyer_async(user_nick: str) -> Dict[str, str]:
    """
    异步AI分析（立即返回）

    返回任务ID，前端轮询获取结果

    性能：< 0.1秒（立即返回，不等待分析完成）
    """
    try:
        # 1. 获取客户数据
        profile = analyzer.get_buyer_profile(user_nick)
        if not profile:
            raise HTTPException(status_code=404, detail=f"客户 {user_nick} 不存在")

        # 2. 获取聊天和订单
        from backend.database import Database, BuyerQueries
        from backend.config import settings

        db = Database(db_name=settings.db_name_to_use or 'aliyunDB')

        query, params = BuyerQueries.get_chat_messages(user_nick, limit=30)
        chats = db.execute_query(query, params)

        orders_query = """
            SELECT 订单号, 商品名称 as commodity_name, category,
                   成交总金额 as payment, 退款金额, 退款类型 as refund_status,
                   最后付款时间 as pay_time
            FROM target_buyer_orders
            WHERE 买家昵称 = %s
            ORDER BY 最后付款时间 DESC
            LIMIT 50
        """
        orders = db.execute_query(orders_query, [user_nick])

        # 3. 创建异步任务
        from backend.ai.task_queue import get_task_manager
        task_manager = get_task_manager()

        task_id = task_manager.create_task(user_nick, profile, chats, orders)

        return {
            "task_id": task_id,
            "status": "pending",
            "message": "AI分析任务已创建，正在后台处理"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> Dict:
    """
    获取异步任务状态

    前端轮询此接口获取分析结果
    """
    from backend.ai.task_queue import get_task_manager
    task_manager = get_task_manager()

    task = task_manager.get_task_status(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "buyer_nick": task.get("buyer_nick"),
        "created_at": task.get("created_at"),
        "result": task.get("result"),
        "error": task.get("error"),
        "completed_at": task.get("completed_at")
    }
```

### 3.3 前端轮询实现

**文件**: `src/hooks/useAIAnalysis.ts`

```typescript
/**
 * AI分析异步任务Hook
 */
import { useState, useCallback, useRef } from 'react';
import api from '../api/client';

interface AnalysisTask {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

export function useAIAnalysis() {
  const [task, setTask] = useState<AnalysisTask | null>(null);
  const [loading, setLoading] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // 启动异步分析
  const startAnalysis = useCallback(async (buyerNick: string) => {
    try {
      setLoading(true);

      // 创建异步任务
      const response = await api.post(`/api/v2/buyers/${encodeURIComponent(buyerNick)}/analyze-async`);
      const taskId = response.task_id;

      setTask({
        task_id: taskId,
        status: 'pending'
      });

      // 开始轮询
      startPolling(taskId);

    } catch (error) {
      console.error('Failed to start analysis:', error);
      setLoading(false);
    }
  }, []);

  // 轮询任务状态
  const startPolling = useCallback((taskId: string) => {
    pollingRef.current = setInterval(async () => {
      try {
        const status = await api.get(`/api/v2/tasks/${taskId}`);

        setTask(status);

        // 完成或失败，停止轮询
        if (status.status === 'completed' || status.status === 'failed') {
          setLoading(false);
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        }

      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 3000); // 每3秒轮询一次
  }, []);

  // 清理
  const cleanup = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  return {
    task,
    loading,
    startAnalysis,
    cleanup
  };
}
```

### 3.4 前端UI集成

**文件**: `src/views/ChatAnalysis.tsx` (示例)

```typescript
import { useAIAnalysis } from '../hooks/useAIAnalysis';

function BuyerProfile({ buyerNick }: { buyerNick: string }) {
  const { task, loading, startAnalysis } = useAIAnalysis();

  const handleAnalyze = () => {
    startAnalysis(buyerNick);
  };

  return (
    <div>
      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? '分析中...' : 'AI分析'}
      </button>

      {/* 任务状态 */}
      {task && (
        <div>
          {task.status === 'pending' && <p>任务排队中...</p>}
          {task.status === 'processing' && <p>正在分析中...</p>}
          {task.status === 'completed' && (
            <div>
              <h3>AI分析结果</h3>
              <p>{task.result?.summary}</p>
            </div>
          )}
          {task.status === 'failed' && (
            <p className="error">分析失败: {task.error}</p>
          )}
        </div>
      )}
    </div>
  );
}
```

### 预期收益

| 指标 | 当前 | 优化后 | 提升 |
|------|------|--------|------|
| API响应时间 | 72秒 | <0.1秒 | **720x** |
| 用户等待体验 | 阻塞72秒 | 立即返回 | ⭐⭐⭐⭐⭐ |
| 并发处理能力 | 1个 | 5个+ | **5x+** |

---

## Phase 4: 成本监控系统 📊

### 目标
实时追踪API使用和成本，避免超预算

### 4.1 成本追踪器

**文件**: `backend/ai/cost_tracker.py`

```python
"""
AI分析成本追踪
实时监控token使用和成本
"""
from datetime import datetime, date
from typing import Dict, List
from collections import defaultdict
import json


class CostTracker:
    """成本追踪器"""

    def __init__(self):
        self.daily_costs: Dict[str, float] = defaultdict(float)
        self.daily_calls: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.budget_threshold = 1000  # 月预算上限（元）

    def track_call(
        self,
        buyer_nick: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int
    ):
        """追踪单次API调用"""
        today = date.today().isoformat()

        # 记录调用次数
        self.daily_calls[today][model] += 1

        # 计算成本
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        self.daily_costs[today] += cost

        # 记录详细日志
        print(f"[成本追踪] {today} | {model} | {buyer_nick}")
        print(f"  - Tokens: {total_tokens} (输入: {input_tokens}, 输出: {output_tokens})")
        print(f"  - 成本: ¥{cost:.4f}")
        print(f"  - 今日累计: ¥{self.daily_costs[today]:.2f}")

        # 预算预警
        monthly_cost = self._get_monthly_cost()
        if monthly_cost > self.budget_threshold * 0.8:
            print(f"⚠️ [预算预警] 本月已使用 ¥{monthly_cost:.2f} / ¥{self.budget_threshold}")

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算单次调用成本（元）"""
        # DeepSeek定价
        if model == "DeepSeek-R1":
            # 输入: ¥1/百万tokens，输出: ¥2/百万tokens
            return (input_tokens * 0.000001 + output_tokens * 0.000002)

        elif model == "DeepSeek-Chat":
            # 统一: ¥1/百万tokens
            return total_tokens * 0.000001

        # Zhipu: 月卡，不计成本
        elif model == "Zhipu-GLM":
            return 0.0

        return 0.0

    def _get_monthly_cost(self) -> float:
        """获取本月累计成本"""
        today = date.today()
        month_start = today.replace(day=1)

        monthly_total = 0.0
        for day_str, cost in self.daily_costs.items():
            day_date = date.fromisoformat(day_str)
            if day_date >= month_start:
                monthly_total += cost

        return monthly_total

    def get_daily_stats(self, day: str = None) -> Dict:
        """获取指定日期的统计"""
        if day is None:
            day = date.today().isoformat()

        return {
            "date": day,
            "total_cost": self.daily_costs.get(day, 0.0),
            "calls_by_model": dict(self.daily_calls.get(day, {}))
        }

    def get_monthly_stats(self) -> Dict:
        """获取本月统计"""
        today = date.today()
        month_start = today.replace(day=1)

        daily_stats = []
        total_cost = 0.0
        total_calls = 0

        for day_str, cost in self.daily_costs.items():
            day_date = date.fromisoformat(day_str)
            if day_date >= month_start and day_date <= today:
                daily_stats.append({
                    "date": day_str,
                    "cost": cost,
                    "calls": dict(self.daily_calls.get(day_str, {}))
                })
                total_cost += cost
                total_calls += sum(self.daily_calls[day_str].values())

        return {
            "month": today.strftime("%Y-%m"),
            "total_cost": total_cost,
            "total_calls": total_calls,
            "daily_breakdown": daily_stats,
            "budget_used": total_cost / self.budget_threshold,
            "budget_remaining": max(0, self.budget_threshold - total_cost)
        }


# 全局单例
_cost_tracker_instance = None


def get_cost_tracker() -> CostTracker:
    """获取成本追踪器单例"""
    global _cost_tracker_instance
    if _cost_tracker_instance is None:
        _cost_tracker_instance = CostTracker()
    return _cost_tracker_instance
```

### 4.2 成本监控API

**文件**: `backend/api/target_routes.py`

```python
@router.get("/ai/cost-stats/daily")
async def get_daily_cost_stats(day: str = None) -> Dict:
    """获取指定日期的成本统计"""
    from backend.ai.cost_tracker import get_cost_tracker
    tracker = get_cost_tracker()
    return tracker.get_daily_stats(day)


@router.get("/ai/cost-stats/monthly")
async def get_monthly_cost_stats() -> Dict:
    """获取本月的成本统计"""
    from backend.ai.cost_tracker import get_cost_tracker
    tracker = get_cost_tracker()
    return tracker.get_monthly_stats()


@router.get("/ai/cost-stats/summary")
async def get_cost_summary() -> Dict:
    """获取成本统计摘要"""
    from backend.ai.cost_tracker import get_cost_tracker
    tracker = get_cost_tracker()

    monthly = tracker.get_monthly_stats()
    daily = tracker.get_daily_stats()

    return {
        "today": daily,
        "month": monthly,
        "budget_threshold": tracker.budget_threshold,
        "alert": monthly["total_cost"] > tracker.budget_threshold * 0.8
    }
```

### 4.3 成本监控Dashboard（前端）

**文件**: `src/components/dashboard/CostMonitor.tsx`

```typescript
/**
 * AI成本监控组件
 */
import { useEffect, useState } from 'react';
import api from '../../api/client';

interface CostSummary {
  today: { total_cost: number; calls_by_model: Record<string, number> };
  month: {
    total_cost: number;
    total_calls: number;
    budget_used: number;
    budget_remaining: number;
  };
  alert: boolean;
}

export function CostMonitor() {
  const [stats, setStats] = useState<CostSummary | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      const data = await api.get('/api/v2/ai/cost-stats/summary');
      setStats(data);
    };

    fetchStats();
    const interval = setInterval(fetchStats, 60000); // 每分钟刷新

    return () => clearInterval(interval);
  }, []);

  if (!stats) return <div>加载中...</div>;

  return (
    <div className="cost-monitor">
      <h3>AI成本监控</h3>

      {/* 今日统计 */}
      <div className="today-stats">
        <h4>今日成本</h4>
        <p className="cost">¥{stats.today.total_cost.toFixed(2)}</p>
        <div className="calls-by-model">
          {Object.entries(stats.today.calls_by_model).map(([model, count]) => (
            <span key={model} className="badge">
              {model}: {count}次
            </span>
          ))}
        </div>
      </div>

      {/* 本月统计 */}
      <div className="month-stats">
        <h4>本月累计</h4>
        <p className="cost">¥{stats.month.total_cost.toFixed(2)}</p>
        <p className="calls">总调用: {stats.month.total_calls}次</p>

        {/* 预算进度条 */}
        <div className="budget-bar">
          <div
            className={`fill ${stats.alert ? 'warning' : ''}`}
            style={{ width: `${stats.month.budget_used * 100}%` }}
          />
          <span>预算使用: {(stats.month.budget_used * 100).toFixed(1)}%</span>
        </div>
        <p className="remaining">剩余: ¥{stats.month.budget_remaining.toFixed(2)}</p>
      </div>

      {/* 预算预警 */}
      {stats.alert && (
        <div className="alert warning">
          ⚠️ 预算预警：本月成本已超过80%
        </div>
      )}
    </div>
  );
}
```

### 预期收益

- 实时成本可见性
- 预算超支预警
- 模型使用占比分析
- 成本优化决策依据

---

## Phase 5: Prompt精细化优化 🎯

### 目标
基于当前使用反馈，优化prompt质量

### 5.1 DeepSeek-R1 Prompt优化

**新增维度**:
```python
# backend/ai/prompts/evidence_extraction.py

# 当前提取的维度：
- 沟通风格
- 消费行为
- 价格敏感度
- 品类偏好

# 新增维度：
EXTRACTION_DIMENSIONS = {
    "价格敏感度": {
        "MD商品占比": "折扣订单数 / 总订单数",
        "平均折扣": "平均折扣金额",
        "结论": ["高", "中", "低"]
    },
    "购买周期": {
        "订单间隔": "计算各订单之间的天数间隔",
        "平均周期": "平均间隔天数",
        "规律": ["稳定", "不规则", "活跃期"]
    },
    "流失风险": {
        "L6M无订单": "boolean",
        "L30D无聊天": "boolean",
        "综合评分": ["高", "中", "低"]
    },
    "推荐品类": {
        "历史偏好": "top_category, second_category",
        "关联推荐": "基于PipES推荐配件、烟草等",
        "价格带": "基于客单价推荐相似价位"
    }
}
```

### 5.2 Zhipu Prompt优化（无聊天客户）

```python
# backend/ai/prompts/zhipu_no_chat.py

ZHIPU_NO_CHAT_PROMPT = """
你是一位电商客户分析专家。客户没有聊天记录，请仅基于消费数据进行分析。

**消费模式分析要求**：

1. **复购周期分析**
   - 第1单 → 第2单间隔：XX天
   - 判断：【快速复购(<30天) | 正常复购(30-90天) | 慢速复购(>90天) | 仅1单】

2. **客单价变化趋势**
   - 首单客单价：¥XXX
   - 最近客单价：¥YYY
   - 判断：【消费升级(上升) | 稳定 | 消费降级(下降)】

3. **品类专注度**
   - 所有订单品类：[PIPES, LIGHTERS, ...]
   - 判断：【专注型(单一品类占比>80%) | 多样化】

4. **促销敏感度**
   - MD商品(折扣)订单占比：XX%
   - 判断：【价格敏感(>50%) | 一般 | 不敏感(<20%)】

**输出要求**：
- summary: 2-3句话，必须包含上述4个维度的具体数字和判断
- key_interests: 基于3和4推断
- recommended_action: 基于2给出具体建议（升级推荐 | 复购提醒 | 促销推荐）
"""
```

### 5.3 行业知识库注入

```python
# backend/ai/prompts/domain_knowledge.py

PIPE_DOMAIN_KNOWLEDGE = """
**烟斗专业知识库**（用于判断客户专业水平）：

【Finish表面处理】
- 喷砂(Rusticated)：防滑，耐用，适合新手
- 光面(Smooth)：显示木纹，需要保养，进阶选择
- 油面：介于两者之间

【Grain纹路】
- 鸟眼纹：极品，昂贵
- 直纹：经典
- 横纹：常见

【Shape斗型】
- 弯斗：咬嘴舒适，老手偏爱
- 直斗：经典款式
- Liverpool: 英式优雅
- Bulldog：稳重霸气

【价格区间】（本品牌定位）
- 入门级：< ¥3,000
- 中档：¥3,000 - ¥10,000
- 高档：> ¥10,000

**判断标准**：
- 老手信号：询问finish、grain、shape具体参数
- 新手信号：问"哪个好"、"怎么选"、"推荐"
"""
```

---

## Phase 6: 批量分析与自动化 🤖

### 目标
自动分析高价值客户，减少手动触发

### 6.1 每日批量分析脚本

**文件**: `scripts/daily_ai_analysis.py`

```python
"""
每日AI分析批量任务
每天凌晨自动分析VIC客户和近期活跃客户
"""
import sys
sys.path.append('.')

from backend.ai.analyzer_orchestrator import get_analyzer_orchestrator
from backend.analytics.target_buyer_analyzer import TargetBuyerAnalyzer
from backend.database import Database
from backend.config import settings
from datetime import datetime, timedelta
import time


def get_target_customers():
    """获取需要分析的目标客户"""
    db = Database(db_name=settings.db_name_to_use or 'aliyunDB')

    # 1. 所有VIC客户
    vic_query = """
        SELECT buyer_nick
        FROM target_buyers_precomputed
        WHERE is_vic = 1
          AND updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        LIMIT 100
    """

    # 2. 最近7天下单的客户
    recent_orders_query = """
        SELECT DISTINCT buyer_nick
        FROM target_buyer_orders
        WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        LIMIT 100
    """

    vic_buyers = db.execute_query(vic_query, [])
    recent_buyers = db.execute_query(recent_orders_query, [])

    # 合并去重
    all_buyers = set([b['buyer_nick'] for b in vic_buyers] +
                     [b['buyer_nick'] for b in recent_buyers])

    return list(all_buyers)


def analyze_buyer(buyer_nick: str, orchestrator, analyzer):
    """分析单个客户"""
    try:
        print(f"\n{'='*60}")
        print(f"分析客户: {buyer_nick}")
        print(f"{'='*60}")

        # 获取profile
        profile = analyzer.get_buyer_profile(buyer_nick)
        if not profile:
            print(f"[跳过] 客户不存在")
            return

        # 检查缓存
        from backend.ai.cache_manager import AICacheManager
        cache_mgr = AICacheManager()
        cached = cache_mgr.get(buyer_nick, profile)

        if cached:
            print(f"[跳过] 缓存命中")
            return

        # 获取聊天和订单
        from backend.database import BuyerQueries

        query, params = BuyerQueries.get_chat_messages(buyer_nick, limit=30)
        chats = db.execute_query(query, params)

        orders_query = """
            SELECT 订单号, 商品名称 as commodity_name, category,
                   成交总金额 as payment, 退款金额, 退款类型 as refund_status,
                   最后付款时间 as pay_time
            FROM target_buyer_orders
            WHERE 买家昵称 = %s
            ORDER BY 最后付款时间 DESC
            LIMIT 50
        """
        orders = db.execute_query(orders_query, [buyer_nick])

        print(f"  - 聊天记录: {len(chats)}条")
        print(f"  - 订单记录: {len(orders)}条")
        print(f"  - VIP等级: {profile.get('vip_level')}")

        # 执行分析
        start = time.time()
        result = orchestrator.analyze_buyer_persona(
            buyer_nick, profile, chats, orders
        )
        elapsed = time.time() - start

        print(f"✅ 分析完成 (耗时: {elapsed:.1f}秒)")
        print(f"   方法: {result.get('analysis_method')}")
        print(f"   成本: ¥{result.get('estimated_cost', 0):.2f}")

        # 限流：避免API限流
        time.sleep(2)

    except Exception as e:
        print(f"❌ 失败: {e}")


def main():
    """主函数"""
    print("="*60)
    print("每日AI分析批量任务")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 初始化
    orchestrator = get_analyzer_orchestrator()
    analyzer = TargetBuyerAnalyzer()
    global db
    db = Database(db_name=settings.db_name_to_use or 'aliyunDB')

    # 获取目标客户
    buyers = get_target_customers()
    print(f"\n待分析客户数: {len(buyers)}")

    # 批量分析
    success_count = 0
    fail_count = 0

    for buyer_nick in buyers:
        try:
            analyze_buyer(buyer_nick, orchestrator, analyzer)
            success_count += 1
        except Exception as e:
            print(f"❌ {buyer_nick} 分析失败: {e}")
            fail_count += 1

    # 统计
    print("\n" + "="*60)
    print("批量分析完成")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


if __name__ == "__main__":
    main()
```

### 6.2 定时任务配置

**Linux Cron**:
```bash
# 每天凌晨2点执行批量分析
0 2 * * * cd /path/to/smokesignal-ecommerce-analytics && python scripts/daily_ai_analysis.py >> logs/daily_analysis.log 2>&1
```

**Windows Task Scheduler**:
```powershell
# 创建定时任务
schtasks /create /tn "Daily AI Analysis" /tr "python D:\Work\ai\projects\smokesignal-ecommerce-analytics\scripts\daily_ai_analysis.py" /sc daily /st 02:00
```

---

## 📅 实施时间表

### Week 1: 缓存 + 智能降级（核心优化）
- ✅ Day 1-2: Redis缓存实现
- ✅ Day 3-4: 智能模型选择策略
- ✅ Day 5: DeepSeek-Chat接口
- ✅ Day 6-7: 测试 + 优化

**预期收益**: 月成本 ¥21,000 → ¥3,300 (84%↓)

### Week 2: 异步处理 + 成本监控
- ✅ Day 8-9: 异步任务队列
- ✅ Day 10-11: 成本追踪系统
- ✅ Day 12: 前端轮询 + UI
- ✅ Day 13: 监控Dashboard
- ✅ Day 14: 测试 + 部署

**预期收益**: 用户体验 ⭐⭐⭐⭐⭐

### Week 3-4: Prompt优化 + 批量分析
- Prompt精细化调整
- 行业知识库注入
- 批量分析脚本
- 定时任务配置

**预期收益**: 分析质量提升 20-30%

---

## 📊 预期整体收益

| 指标 | 当前 | Phase 1+2 | Phase 1-4全部 | 提升 |
|------|------|-----------|--------------|------|
| 首次响应时间 | 72秒 | 72秒 | 72秒 | - |
| 缓存命中响应 | 72秒 | <0.1秒 | <0.1秒 | **720x** |
| 月度API调用 | 3000次 | 600次 | 90次 | **97%↓** |
| 月度DeepSeek成本 | ¥21,000 | ¥3,300 | ¥990 | **95%↓** |
| 并发处理能力 | 1个 | 1个 | 5个+ | **5x+** |
| 用户体验评分 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⬆️3星 |

---

## 🎯 成功指标

### 性能指标
- 缓存命中率 > 70%
- API响应时间（缓存）< 0.1秒
- 异步任务创建时间 < 0.1秒

### 成本指标
- 月度成本 < ¥1,000 (优化前¥21,000)
- Zhipu使用率 > 60%
- DeepSeek-R1使用率 < 10%

### 质量指标
- 用户反馈评分 > 4.0/5.0
- AI分析可用率 > 95%
- 规则引擎兜底率 < 5%

---

## 📝 注意事项

### Redis部署
- 开发环境：本地Redis
- 生产环境：阿里云Redis / AWS ElastiCache

### 并发控制
- DeepSeek API限流：未公开，保守估计5并发
- 建议使用信号量控制并发数

### 成本监控
- 设置月度预算上限：¥1,000
- 超过80%发送预警
- 超过100%自动降级到Zhipu

### Prompt迭代
- 每月review用户反馈
- A/B测试新prompt版本
- 保留优秀案例分析

---

**文档版本**: v1.1
**最后更新**: 2026-02-24
**负责人**: AI Team
**状态**: 部分完成 (Phase 1-2 已实现)

---

## ✅ 已完成的优化

详见: [2026-02-24-ai-optimization-summary.md](./2026-02-24-ai-optimization-summary.md)

| Phase | 功能 | 状态 |
|-------|------|------|
| Phase 1 | MySQL缓存机制 | ✅ 完成 |
| Phase 1 | 动态TTL策略 | ✅ 完成 |
| Phase 1 | 缓存验证机制 | ✅ 完成 |
| Phase 2 | 多级降级策略 | ✅ 完成 |
| Phase 2 | 429错误自动降级 | ✅ 完成 |
| Phase 2 | GLM-4.7备选模型 | ✅ 完成 |
| Phase 3 | 异步处理 | ⏳ 待实施 |
| Phase 4 | 成本监控 | ⏳ 待实施 |
| Phase 5 | Prompt优化 | ⏳ 待实施 |
| Phase 6 | 批量分析 | ⏳ 待实施 |
