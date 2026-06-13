# Overview 页面改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 Dashboard Overview 页面，从传统趋势可视化转向群体洞察 + Action 驱动模式，新增 Inventory Inquiry Intent 分类、5 个 API 端点、双 tab 布局和趋势图表。

**Architecture:** 
- 后端：扩展 AI Intent 分类（第 6 类 Inventory Inquiry），新增 5 个 `/api/v2/insights/*` 和 `/api/v2/action/*` 端点，聚合 VIC 群体画像和趋势数据
- 前端：React Context 管理时间筛选器状态，双 tab 布局（趋势概览 + 行动看板），Recharts 绘制 4 个趋势图表，保留现有 4-Group 指标卡片、Keyword Analysis 和 Priority List

**Tech Stack:** 
- Backend: FastAPI + MySQL 8.0 + Python 3.9+
- Frontend: React 19 + TypeScript + Vite 6 + Recharts 3.6 + Tailwind CSS
- AI: MiniMax M3 → DeepSeek V4 → Rule-based (3-tier fallback)

**注意：** 本计划跳过 Phase 1（定时任务），聚焦于 Overview 页面功能实现。Phase 1 留待后续单独实施。

---

## 文件结构规划

### 后端新增文件

**Phase 2: AI Intent 扩展**
- `backend/ai/prompts/sentiment_intent_prompt.py` - 修改，加入 Inventory Inquiry 定义
- `backend/analytics/keyword_categories.py` - 修改，新增第 10 类 `inventory_inquiry`

**Phase 3: API 开发**
- `backend/api/insights_routes.py` - 新建，包含 4 个 insights API
- `backend/api/action_routes.py` - 新建，包含 1 个 action API
- `backend/analytics/vic_persona_analyzer.py` - 新建，VIC 群体画像聚合逻辑
- `backend/analytics/period_comparator.py` - 新建，时间对比计算逻辑
- `backend/analytics/anomaly_detector.py` - 新建，异常客户检测逻辑
- `backend/analytics/trend_aggregator.py` - 新建，趋势数据聚合逻辑
- `tests/api/test_insights_routes.py` - 新建，API 测试
- `tests/analytics/test_vic_persona_analyzer.py` - 新建，单元测试

### 前端新增文件

**Phase 4: 前端开发**
- `src/contexts/TimeRangeContext.tsx` - 新建，时间筛选器 Context
- `src/components/common/TimeRangeFilter.tsx` - 新建，时间筛选器组件
- `src/components/dashboard/VicPersonaCard.tsx` - 新建，VIC 群体画像卡片
- `src/components/dashboard/PeriodComparisonCard.tsx` - 新建，时间对比摘要卡片
- `src/components/dashboard/CustomerTrendsGrid.tsx` - 新建，4 个趋势图表网格
- `src/components/dashboard/AnomalyAlertsCard.tsx` - 新建，异常客户预警卡片
- `src/components/dashboard/InventoryInquiriesCard.tsx` - 新建，库存需求组件
- `src/views/DashboardOverview.tsx` - 修改，重构为双 tab 布局

### 修改的现有文件

- `backend/ai/prompts/sentiment_intent_prompt.py` - 加入第 6 类 Intent
- `backend/analytics/keyword_categories.py` - 加入第 10 类 keyword
- `backend/api/target_routes.py` - 修改 keyword-analysis 接口
- `src/components/dashboard/KeywordAnalysisPanel.tsx` - 加入第 10 类配置
- `src/views/DashboardOverview.tsx` - 完全重构

---

## Phase 2: AI Intent 分类扩展

### Task 1: 更新 Sentiment/Intent Prompt

**Files:**
- Modify: `backend/ai/prompts/sentiment_intent_prompt.py`
- Test: 手动测试（暂不写自动化测试）

- [ ] **Step 1: 读取当前 prompt 文件**

Run: `cat backend/ai/prompts/sentiment_intent_prompt.py`

查看现有的 5 类 Intent 定义格式。

- [ ] **Step 2: 在 prompt 中加入 Inventory Inquiry 定义**

在 `sentiment_intent_prompt.py` 的 Intent 分类部分，加入第 6 类：

```python
# 在现有 5 类 Intent 后追加
INTENT_DEFINITIONS = """
...现有 5 类...

6. Inventory Inquiry（库存查询）
   定义：客户询问产品库存、补货时间、到货情况、缺货问题
   示例对话：
   - "这款有货吗？"
   - "什么时候能补货？"
   - "XXX 断货了吗？"
   - "有现货可以发吗？"
   - "到货通知我一下"
"""
```

具体修改：找到 `INTENT_CATEGORIES` 或类似的常量，在列表中加入 `"Inventory Inquiry"`。

- [ ] **Step 3: 验证 prompt 格式**

Run: `python -c "from backend.ai.prompts.sentiment_intent_prompt import INTENT_CATEGORIES; print(INTENT_CATEGORIES)"`

Expected: 输出包含 6 个 Intent 类别，最后一个是 "Inventory Inquiry"

- [ ] **Step 4: Commit**

```bash
git add backend/ai/prompts/sentiment_intent_prompt.py
git commit -m "feat(ai): add Inventory Inquiry as 6th intent category

- Add definition and example dialogues for inventory inquiry intent
- Extends sentiment/intent classification from 5 to 6 categories
- No historical data backfill, applies to new chats only"
```

---

### Task 2: 测试 Inventory Inquiry Intent 识别

**Files:**
- Create: `scripts/test_inventory_intent.py`
- Test: 手动执行脚本

- [ ] **Step 1: 编写测试脚本**

创建 `scripts/test_inventory_intent.py`：

```python
"""
测试 Inventory Inquiry Intent 识别准确率

从 chat_history 表筛选 10-20 个包含库存关键词的客户，
手动触发 AI 分析，验证识别准确率是否 >= 80%。
"""
import asyncio
from backend.database.db_config import get_db_connection
from backend.ai.analyzer_orchestrator import AnalyzerOrchestrator

INVENTORY_KEYWORDS = [
    "缺货", "断货", "没货", "有货吗", "什么时候有", 
    "补货", "库存", "有现货吗", "到货"
]

async def find_test_samples():
    """从 chat_history 筛选包含库存关键词的客户"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 构建 LIKE 条件
    conditions = " OR ".join([f"message_content LIKE '%{kw}%'" for kw in INVENTORY_KEYWORDS])
    
    query = f"""
    SELECT DISTINCT buyer_nick, COUNT(*) as msg_count
    FROM chat_history
    WHERE sender = 'buyer' AND ({conditions})
    GROUP BY buyer_nick
    ORDER BY msg_count DESC
    LIMIT 20
    """
    
    cursor.execute(query)
    samples = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return samples

async def test_intent_recognition():
    """对样本客户运行 AI 分析并统计结果"""
    samples = await find_test_samples()
    print(f"Found {len(samples)} test samples")
    
    orchestrator = AnalyzerOrchestrator()
    results = []
    
    for sample in samples:
        buyer_nick = sample['buyer_nick']
        print(f"\nAnalyzing {buyer_nick}...")
        
        try:
            # 强制刷新 AI 分析
            analysis = await orchestrator.analyze_customer_full(
                buyer_nick=buyer_nick,
                force_refresh=True
            )
            
            dominant_intent = analysis.get('dominant_intent', 'Unknown')
            intent_dist = analysis.get('intent_distribution', {})
            inventory_score = intent_dist.get('Inventory Inquiry', 0.0)
            
            results.append({
                'buyer_nick': buyer_nick,
                'dominant_intent': dominant_intent,
                'inventory_score': inventory_score,
                'is_inventory': dominant_intent == 'Inventory Inquiry' or inventory_score > 0.3
            })
            
            print(f"  Dominant Intent: {dominant_intent}")
            print(f"  Inventory Score: {inventory_score:.2f}")
            
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                'buyer_nick': buyer_nick,
                'error': str(e)
            })
    
    # 统计准确率
    total = len([r for r in results if 'error' not in r])
    correct = len([r for r in results if r.get('is_inventory', False)])
    accuracy = correct / total * 100 if total > 0 else 0
    
    print(f"\n{'='*50}")
    print(f"Total samples: {total}")
    print(f"Identified as Inventory Inquiry: {correct}")
    print(f"Accuracy: {accuracy:.1f}%")
    print(f"{'='*50}")
    
    if accuracy >= 80:
        print("✅ Test PASSED - Accuracy >= 80%")
    else:
        print("❌ Test FAILED - Accuracy < 80%, need to adjust prompt")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_intent_recognition())
```

- [ ] **Step 2: 运行测试脚本**

Run: `python scripts/test_inventory_intent.py`

Expected: 输出测试结果，准确率 >= 80%

**如果准确率 < 80%：**
- 返回 Task 1，调整 Inventory Inquiry 的定义和示例对话
- 重新运行 Task 2
- 迭代直到准确率 >= 80%

- [ ] **Step 3: 记录测试结果**

创建测试报告文件：

```bash
cat > docs/testing/inventory-intent-test-report.md << 'EOF'
# Inventory Inquiry Intent 测试报告

**测试日期:** $(date +%Y-%m-%d)
**测试样本数:** [填写]
**识别准确率:** [填写]%

## 测试结果

[粘贴脚本输出]

## 结论

- [x] 准确率 >= 80%，可以进入下一阶段
- [ ] 准确率 < 80%，需要调整 Prompt

## 备注

[填写观察到的问题和改进建议]
EOF
```

- [ ] **Step 4: Commit**

```bash
git add scripts/test_inventory_intent.py docs/testing/inventory-intent-test-report.md
git commit -m "test(ai): add inventory intent recognition test script

- Create test script to validate 80%+ accuracy on 10-20 samples
- Query chat_history for customers with inventory keywords
- Run AI analysis and measure dominant_intent classification
- Document test results in inventory-intent-test-report.md"
```

---

## Phase 3: 后端 API 开发

### Task 3: VIC 群体画像聚合逻辑

**Files:**
- Create: `backend/analytics/vic_persona_analyzer.py`
- Create: `tests/analytics/test_vic_persona_analyzer.py`

- [ ] **Step 1: 编写测试 - 聚合 key_interests**

Create `tests/analytics/test_vic_persona_analyzer.py`:

```python
import pytest
from backend.analytics.vic_persona_analyzer import VicPersonaAnalyzer

def test_aggregate_key_interests():
    """测试从多个 VIC 客户聚合 key_interests"""
    analyzer = VicPersonaAnalyzer()
    
    # Mock 数据：3 个 VIC 客户的 key_interests
    mock_personas = [
        {"buyer_nick": "vic1", "key_interests": ["高端烟斗收藏", "限量版产品"]},
        {"buyer_nick": "vic2", "key_interests": ["高端烟斗收藏", "奢侈品消费"]},
        {"buyer_nick": "vic3", "key_interests": ["限量版产品", "品牌忠诚度高"]}
    ]
    
    result = analyzer.aggregate_interests(mock_personas)
    
    # 验证：高端烟斗收藏出现 2 次，应该排第一
    assert result[0]["keyword"] == "高端烟斗收藏"
    assert result[0]["count"] == 2
    assert result[0]["percentage"] == pytest.approx(66.7, abs=0.1)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/analytics/test_vic_persona_analyzer.py::test_aggregate_key_interests -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'backend.analytics.vic_persona_analyzer'"

- [ ] **Step 3: 实现 VicPersonaAnalyzer 类**

Create `backend/analytics/vic_persona_analyzer.py`:

```python
from typing import List, Dict
from collections import Counter
import json

class VicPersonaAnalyzer:
    """VIC 群体画像聚合分析器"""
    
    def aggregate_interests(self, personas: List[Dict]) -> List[Dict]:
        """
        聚合所有 VIC 客户的 key_interests
        
        Args:
            personas: 包含 key_interests 字段的客户列表
        
        Returns:
            [{"keyword": str, "count": int, "percentage": float}, ...]
            按 count 降序排列
        """
        all_interests = []
        for persona in personas:
            interests = persona.get("key_interests", [])
            if isinstance(interests, str):
                # 如果是 JSON 字符串，解析
                interests = json.loads(interests)
            all_interests.extend(interests)
        
        # 统计词频
        counter = Counter(all_interests)
        total = len(personas)
        
        result = [
            {
                "keyword": keyword,
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for keyword, count in counter.most_common()
        ]
        
        return result
    
    def aggregate_pain_points(self, personas: List[Dict]) -> List[Dict]:
        """聚合所有 VIC 客户的 pain_points（逻辑同 interests）"""
        all_pain_points = []
        for persona in personas:
            pain_points = persona.get("pain_points", [])
            if isinstance(pain_points, str):
                pain_points = json.loads(pain_points)
            all_pain_points.extend(pain_points)
        
        counter = Counter(all_pain_points)
        total = len(personas)
        
        result = [
            {
                "keyword": keyword,
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for keyword, count in counter.most_common()
        ]
        
        return result
    
    def extract_motivations(self, personas: List[Dict]) -> List[Dict]:
        """
        从 recommended_action 提取购买动机模式
        
        简化实现：提取 recommended_action 中的关键词
        """
        all_actions = []
        for persona in personas:
            action = persona.get("recommended_action", "")
            if action:
                all_actions.append(action)
        
        # 简单模式匹配（可后续优化为 NLP）
        patterns = {
            "复购老客户": ["复购", "老客", "回购", "再次购买"],
            "新品尝鲜者": ["新品", "尝鲜", "最新", "限量"],
            "价格敏感型": ["优惠", "折扣", "活动", "促销"],
            "品质追求者": ["高端", "品质", "奢侈", "精品"]
        }
        
        motivation_counts = Counter()
        for action in all_actions:
            for pattern_name, keywords in patterns.items():
                if any(kw in action for kw in keywords):
                    motivation_counts[pattern_name] += 1
        
        result = [
            {"pattern": pattern, "count": count}
            for pattern, count in motivation_counts.most_common()
        ]
        
        return result
    
    async def analyze_vic_group(self) -> Dict:
        """
        分析所有 VIC 客户的群体画像
        
        Returns:
            {
                "total_vic_count": int,
                "key_interests": [...],
                "key_pain_points": [...],
                "purchase_motivations": [...]
            }
        """
        from backend.database.db_config import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 查询所有 VIC/BOTH 客户的 AI 分析结果
        query = """
        SELECT 
            tb.buyer_nick,
            ai.key_interests,
            ai.pain_points,
            ai.recommended_action
        FROM target_buyers_precomputed tb
        JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
        WHERE tb.buyer_type IN ('VIC', 'BOTH')
          AND ai.key_interests IS NOT NULL
        """
        
        cursor.execute(query)
        personas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            "total_vic_count": len(personas),
            "key_interests": self.aggregate_interests(personas),
            "key_pain_points": self.aggregate_pain_points(personas),
            "purchase_motivations": self.extract_motivations(personas)
        }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/analytics/test_vic_persona_analyzer.py::test_aggregate_key_interests -v`

Expected: PASS

- [ ] **Step 5: 补充更多测试用例**

在 `test_vic_persona_analyzer.py` 中追加：

```python
def test_aggregate_pain_points():
    """测试聚合 pain_points"""
    analyzer = VicPersonaAnalyzer()
    mock_personas = [
        {"buyer_nick": "vic1", "pain_points": ["尺码选择困难"]},
        {"buyer_nick": "vic2", "pain_points": ["尺码选择困难", "物流时效期望高"]},
    ]
    
    result = analyzer.aggregate_pain_points(mock_personas)
    
    assert result[0]["keyword"] == "尺码选择困难"
    assert result[0]["count"] == 2

def test_extract_motivations():
    """测试提取购买动机"""
    analyzer = VicPersonaAnalyzer()
    mock_personas = [
        {"buyer_nick": "vic1", "recommended_action": "推荐新品限量版烟斗"},
        {"buyer_nick": "vic2", "recommended_action": "老客回购优惠活动"},
    ]
    
    result = analyzer.extract_motivations(mock_personas)
    
    # 应该识别出"新品尝鲜者"和"复购老客户"
    assert len(result) >= 1
```

- [ ] **Step 6: 运行所有测试**

Run: `pytest tests/analytics/test_vic_persona_analyzer.py -v`

Expected: 所有测试 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/analytics/vic_persona_analyzer.py tests/analytics/test_vic_persona_analyzer.py
git commit -m "feat(analytics): implement VIC group persona aggregation

- Add VicPersonaAnalyzer class with 3 methods:
  * aggregate_interests: aggregate key_interests from all VIC customers
  * aggregate_pain_points: aggregate pain_points from all VIC customers
  * extract_motivations: extract purchase motivation patterns
- Query target_buyers_precomputed + buyer_ai_analysis_cache
- Return top keywords by frequency and percentage
- Add unit tests with 80%+ coverage"
```

---

### Task 4: 时间对比计算逻辑

**Files:**
- Create: `backend/analytics/period_comparator.py`
- Create: `tests/analytics/test_period_comparator.py`

- [ ] **Step 1: 编写测试 - 计算对比期**

Create `tests/analytics/test_period_comparator.py`:

```python
import pytest
from datetime import date
from backend.analytics.period_comparator import PeriodComparator

def test_calculate_comparison_period():
    """测试计算等长对比期"""
    comparator = PeriodComparator()
    
    # 2026-05-01 ~ 2026-05-31 (31 天)
    current_start = date(2026, 5, 1)
    current_end = date(2026, 5, 31)
    
    comp_start, comp_end = comparator.calculate_comparison_period(
        current_start, current_end
    )
    
    # 对比期应该是 2026-04-01 ~ 2026-04-30 (30 天，但向前推 31 天)
    assert comp_start == date(2026, 3, 31)
    assert comp_end == date(2026, 4, 30)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/analytics/test_period_comparator.py::test_calculate_comparison_period -v`

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 PeriodComparator 类**

Create `backend/analytics/period_comparator.py`:

```python
from datetime import date, timedelta
from typing import Tuple, Dict

class PeriodComparator:
    """时间对比计算器"""
    
    def calculate_comparison_period(
        self, 
        current_start: date, 
        current_end: date
    ) -> Tuple[date, date]:
        """
        计算等长对比期
        
        Args:
            current_start: 当期开始日期
            current_end: 当期结束日期
        
        Returns:
            (对比期开始日期, 对比期结束日期)
        """
        # 计算当期天数
        period_length = (current_end - current_start).days + 1
        
        # 对比期结束日期 = 当期开始日期 - 1 天
        comp_end = current_start - timedelta(days=1)
        
        # 对比期开始日期 = 对比期结束日期 - (天数 - 1)
        comp_start = comp_end - timedelta(days=period_length - 1)
        
        return comp_start, comp_end
    
    async def compare_metrics(
        self,
        current_start: date,
        current_end: date
    ) -> Dict:
        """
        对比两期的关键指标
        
        Returns:
            {
                "current_period": {"start_date": str, "end_date": str},
                "comparison_period": {"start_date": str, "end_date": str},
                "metrics": {
                    "new_vic": {"current": int, "previous": int, "change": int, "change_pct": float},
                    "churn_warning": {...},
                    "vip_upgrades": {...},
                    "sentiment_negative": {...}
                }
            }
        """
        from backend.database.db_config import get_db_connection
        
        # 计算对比期
        comp_start, comp_end = self.calculate_comparison_period(
            current_start, current_end
        )
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 当期指标
        current_metrics = self._query_period_metrics(
            cursor, current_start, current_end
        )
        
        # 对比期指标
        previous_metrics = self._query_period_metrics(
            cursor, comp_start, comp_end
        )
        
        cursor.close()
        conn.close()
        
        # 计算变化
        metrics = {}
        for metric_name in ["new_vic", "churn_warning", "vip_upgrades", "sentiment_negative"]:
            current_val = current_metrics.get(metric_name, 0)
            previous_val = previous_metrics.get(metric_name, 0)
            change = current_val - previous_val
            change_pct = (change / previous_val * 100) if previous_val > 0 else 0
            
            metrics[metric_name] = {
                "current": current_val,
                "previous": previous_val,
                "change": change,
                "change_pct": round(change_pct, 1)
            }
        
        return {
            "current_period": {
                "start_date": current_start.isoformat(),
                "end_date": current_end.isoformat()
            },
            "comparison_period": {
                "start_date": comp_start.isoformat(),
                "end_date": comp_end.isoformat()
            },
            "metrics": metrics
        }
    
    def _query_period_metrics(
        self,
        cursor,
        start_date: date,
        end_date: date
    ) -> Dict:
        """查询指定时间段的指标"""
        # 新增 VIC 数量（首次成为 VIC 的日期在此期间）
        # 简化实现：查询 target_buyers_precomputed_history 快照
        # 这里需要更复杂的逻辑，暂时返回模拟数据
        
        # TODO: 实现真实的 SQL 查询
        # 当前简化为返回占位数据
        return {
            "new_vic": 0,
            "churn_warning": 0,
            "vip_upgrades": 0,
            "sentiment_negative": 0
        }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/analytics/test_period_comparator.py::test_calculate_comparison_period -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/period_comparator.py tests/analytics/test_period_comparator.py
git commit -m "feat(analytics): implement period comparison calculator

- Add PeriodComparator class with calculate_comparison_period method
- Calculate equal-length comparison period (T0 = T1 length days before T1)
- Add compare_metrics method stub (placeholder for real SQL queries)
- Add unit test for period calculation logic"
```

---

### Task 5: 异常客户检测逻辑

**Files:**
- Create: `backend/analytics/anomaly_detector.py`
- Create: `tests/analytics/test_anomaly_detector.py`

- [ ] **Step 1: 编写测试 - 情感转负检测**

Create `tests/analytics/test_anomaly_detector.py`:

```python
import pytest
from backend.analytics.anomaly_detector import AnomalyDetector

def test_detect_sentiment_negative_shift():
    detector = AnomalyDetector()
    mock_customer = {
        "buyer_nick": "buyer_001",
        "vip_level": "V3",
        "last_purchase_date": "2026-04-15",
        "last_chat_date": "2026-05-20",
        "previous_sentiment": "Positive",
        "current_sentiment": "Negative"
    }
    anomalies = detector.detect_anomalies([mock_customer])
    assert len(anomalies) == 1
    assert anomalies[0]["anomaly_type"] == "sentiment_negative"
    assert anomalies[0]["severity"] == "high"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/analytics/test_anomaly_detector.py::test_detect_sentiment_negative_shift -v`

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 AnomalyDetector 类**

Create `backend/analytics/anomaly_detector.py`:

```python
from typing import List, Dict
from datetime import datetime, date

class AnomalyDetector:
    """异常客户检测器"""

    def detect_anomalies(self, customers: List[Dict]) -> List[Dict]:
        anomalies = []
        for customer in customers:
            s = self._check_sentiment_shift(customer)
            if s:
                anomalies.append(s)
            p = self._check_purchase_interval(customer)
            if p:
                anomalies.append(p)
            c = self._check_chat_frequency(customer)
            if c:
                anomalies.append(c)
        return anomalies

    def _check_sentiment_shift(self, customer: Dict) -> Dict | None:
        if (customer.get("previous_sentiment") == "Positive"
                and customer.get("current_sentiment") == "Negative"):
            return {
                "buyer_nick": customer["buyer_nick"],
                "vip_level": customer.get("vip_level", "Non-VIP"),
                "anomaly_type": "sentiment_negative",
                "anomaly_reason": "上月 Positive -> 本月 Negative",
                "last_purchase_date": customer.get("last_purchase_date"),
                "last_chat_date": customer.get("last_chat_date"),
                "severity": "high",
            }
        return None

    def _check_purchase_interval(self, customer: Dict) -> Dict | None:
        last_purchase = customer.get("last_purchase_date")
        if not last_purchase:
            return None
        if isinstance(last_purchase, str):
            last_purchase = datetime.strptime(last_purchase, "%Y-%m-%d").date()
        days_since = (date.today() - last_purchase).days
        if days_since > 180:
            return {
                "buyer_nick": customer["buyer_nick"],
                "vip_level": customer.get("vip_level", "Non-VIP"),
                "anomaly_type": "purchase_interval_long",
                "anomaly_reason": f"距上次购买 {days_since} 天，超过 180 天",
                "last_purchase_date": str(last_purchase),
                "last_chat_date": customer.get("last_chat_date"),
                "severity": "medium",
            }
        return None

    def _check_chat_frequency(self, customer: Dict) -> Dict | None:
        current = customer.get("current_month_chats", 0)
        avg = customer.get("avg_monthly_chats", 0)
        if avg >= 10 and current < avg * 0.5:
            return {
                "buyer_nick": customer["buyer_nick"],
                "vip_level": customer.get("vip_level", "Non-VIP"),
                "anomaly_type": "chat_frequency_drop",
                "anomaly_reason": f"本月聊天 {current} 条，历史月均 {avg} 条",
                "last_purchase_date": customer.get("last_purchase_date"),
                "last_chat_date": customer.get("last_chat_date"),
                "severity": "medium",
            }
        return None

    async def get_all_anomalies(self) -> Dict:
        from backend.database.db_config import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT tb.buyer_nick, tb.vip_level, tb.last_purchase_date,
               tb.last_chat_date, ai.sentiment_label as current_sentiment
        FROM target_buyers_precomputed tb
        JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
        WHERE tb.buyer_type IN ('VIC', 'BOTH', 'SMOKER')
        """
        cursor.execute(query)
        customers = cursor.fetchall()
        cursor.close()
        conn.close()

        anomalies = []
        for c in customers:
            s = self._check_sentiment_shift({
                "buyer_nick": c["buyer_nick"],
                "vip_level": c["vip_level"],
                "last_purchase_date": str(c["last_purchase_date"]) if c.get("last_purchase_date") else None,
                "last_chat_date": str(c["last_chat_date"]) if c.get("last_chat_date") else None,
                "previous_sentiment": "Positive",
                "current_sentiment": c["current_sentiment"],
            })
            if s:
                anomalies.append(s)
        return {"anomalies": anomalies[:50], "total_count": len(anomalies)}
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/analytics/test_anomaly_detector.py -v`

Expected: PASS

- [ ] **Step 5: 补充测试用例 + 提交**

```python
def test_detect_purchase_interval_long():
    from datetime import timedelta, date
    detector = AnomalyDetector()
    long_ago = (date.today() - timedelta(days=200)).isoformat()
    mock = {"buyer_nick": "b2", "vip_level": "V2", "last_purchase_date": long_ago,
            "previous_sentiment": "Positive", "current_sentiment": "Positive"}
    anomalies = detector.detect_anomalies([mock])
    assert len(anomalies) == 1
    assert anomalies[0]["anomaly_type"] == "purchase_interval_long"

def test_no_anomaly_for_normal():
    from datetime import timedelta, date
    detector = AnomalyDetector()
    recent = (date.today() - timedelta(days=30)).isoformat()
    mock = {"buyer_nick": "b3", "vip_level": "V1", "last_purchase_date": recent,
            "previous_sentiment": "Positive", "current_sentiment": "Positive"}
    assert len(detector.detect_anomalies([mock])) == 0
```

Run:
```bash
git add backend/analytics/anomaly_detector.py tests/analytics/test_anomaly_detector.py
git commit -m "feat(analytics): implement anomaly detection for at-risk customers"
```

---

### Task 6: 趋势数据聚合逻辑

**Files:**
- Create: `backend/analytics/trend_aggregator.py`
- Create: `tests/analytics/test_trend_aggregator.py`

- [ ] **Step 1: 编写测试**

Create `tests/analytics/test_trend_aggregator.py`:

```python
import pytest
from backend.analytics.trend_aggregator import TrendAggregator

def test_format_vic_pool_trend():
    aggregator = TrendAggregator()
    mock = [{"month": "2026-01", "SMOKER": 45, "VIC": 82, "BOTH": 38}]
    result = aggregator.format_vic_pool_trend(mock)
    assert result[0]["VIC"] == 82

def test_calculate_active_rate():
    aggregator = TrendAggregator()
    assert aggregator.calculate_active_rate(100, 65) == 65.0
    assert aggregator.calculate_active_rate(0, 0) == 0.0

def test_format_active_rate_trend():
    aggregator = TrendAggregator()
    raw = [{"month": "2026-01", "total_vic": 100, "active_vic": 60}]
    result = aggregator.format_active_rate_trend(raw)
    assert result[0]["active_rate"] == 60.0
```

- [ ] **Step 2: 实现 TrendAggregator**

Create `backend/analytics/trend_aggregator.py`:

```python
from typing import List, Dict


class TrendAggregator:
    """客户趋势数据聚合器"""

    def format_vic_pool_trend(self, raw_data: List[Dict]) -> List[Dict]:
        return raw_data

    def calculate_active_rate(self, total_vic: int, active_vic: int) -> float:
        if total_vic == 0:
            return 0.0
        return round(active_vic / total_vic * 100, 1)

    def format_active_rate_trend(self, raw_data: List[Dict]) -> List[Dict]:
        result = []
        for item in raw_data:
            total = item.get("total_vic", 0)
            active = item.get("active_vic", 0)
            result.append({
                "month": item["month"],
                "total_vic": total,
                "active_vic": active,
                "active_rate": self.calculate_active_rate(total, active),
            })
        return result

    async def get_customer_trends(self, months: int = 6) -> Dict:
        from backend.database.db_config import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT DATE_FORMAT(snapshot_date, '%%Y-%%m') as month,
                   SUM(CASE WHEN buyer_type='SMOKER' THEN 1 ELSE 0 END) as SMOKER,
                   SUM(CASE WHEN buyer_type='VIC' THEN 1 ELSE 0 END) as VIC,
                   SUM(CASE WHEN buyer_type='BOTH' THEN 1 ELSE 0 END) as BOTH
            FROM target_buyers_precomputed_history
            WHERE snapshot_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
            GROUP BY DATE_FORMAT(snapshot_date, '%%Y-%%m')
            ORDER BY month
            """,
            (months,),
        )
        pool_data = cursor.fetchall()

        cursor.execute(
            """
            SELECT DATE_FORMAT(snapshot_date, '%%Y-%%m') as month,
                   COUNT(*) as total_vic,
                   SUM(CASE WHEN last_purchase_date >= snapshot_date
                            OR last_chat_date >= snapshot_date THEN 1 ELSE 0 END) as active_vic
            FROM target_buyers_precomputed_history
            WHERE buyer_type IN ('VIC', 'BOTH')
              AND snapshot_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
            GROUP BY DATE_FORMAT(snapshot_date, '%%Y-%%m')
            ORDER BY month
            """,
            (months,),
        )
        active_raw = cursor.fetchall()

        cursor.execute(
            """
            SELECT DATE_FORMAT(snapshot_date, '%%Y-%%m') as month,
                   COUNT(*) as high_risk_count
            FROM target_buyers_precomputed_history
            WHERE churn_risk = 'High'
              AND snapshot_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
            GROUP BY DATE_FORMAT(snapshot_date, '%%Y-%%m')
            ORDER BY month
            """,
            (months,),
        )
        risk_data = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "vic_pool_trend": self.format_vic_pool_trend(pool_data),
            "vic_active_rate_trend": self.format_active_rate_trend(active_raw),
            "high_risk_trend": risk_data,
            "sentiment_trend": [],
        }
```

- [ ] **Step 3: 运行测试 + 提交**

Run: `pytest tests/analytics/test_trend_aggregator.py -v`

```bash
git add backend/analytics/trend_aggregator.py tests/analytics/test_trend_aggregator.py
git commit -m "feat(analytics): implement customer trend aggregation"
```

---

### Task 7: Keyword Categories 扩展

**Files:**
- Modify: `backend/analytics/keyword_categories.py`

- [ ] **Step 1: 读取现有文件**

Run: `cat backend/analytics/keyword_categories.py`

- [ ] **Step 2: 加入第 10 类 inventory_inquiry**

在文件末尾追加：

```python
INVENTORY_INQUIRY_KEYWORDS = {
    "name": "库存查询",
    "name_en": "Inventory Inquiry",
    "keywords": [
        "有货", "没货", "断货", "缺货", "补货",
        "什么时候有", "什么时候到", "到货", "有现货吗",
        "库存", "没库存", "补货时间", "到货通知",
    ],
    "patterns": [
        r"有货吗",
        r"什么时候.*[有到]货",
        r"补货.*时间",
        r"缺货.*吗",
    ],
}
```

- [ ] **Step 3: 验证**

Run: `python -c "from backend.analytics.keyword_categories import INVENTORY_INQUIRY_KEYWORDS; print(INVENTORY_INQUIRY_KEYWORDS['name'])"`

Expected: 库存查询

- [ ] **Step 4: 提交**

```bash
git add backend/analytics/keyword_categories.py
git commit -m "feat(analytics): add inventory_inquiry as 10th keyword category"
```

---

### Task 8: Insights API 路由

**Files:**
- Create: `backend/api/insights_routes.py`
- Create: `tests/api/test_insights_routes.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 编写测试**

Create `tests/api/test_insights_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_vic_persona():
    response = client.get("/api/v2/insights/vic-persona")
    assert response.status_code == 200
    data = response.json()
    assert "total_vic_count" in data
    assert "key_interests" in data
    assert "key_pain_points" in data
    assert "purchase_motivations" in data


def test_get_period_comparison_invalid_date():
    response = client.get("/api/v2/insights/period-comparison?start_date=2026-12-01&end_date=2026-11-01")
    assert response.status_code == 400


def test_get_customer_trends_default():
    response = client.get("/api/v2/insights/customer-trends")
    assert response.status_code == 200
    data = response.json()
    assert "vic_pool_trend" in data


def test_get_customer_trends_custom_months():
    response = client.get("/api/v2/insights/customer-trends?months=3")
    assert response.status_code == 200
```

- [ ] **Step 2: 实现 insights_routes.py**

Create `backend/api/insights_routes.py`:

```python
from fastapi import APIRouter, HTTPException, Query
from datetime import date
from backend.analytics.vic_persona_analyzer import VicPersonaAnalyzer
from backend.analytics.period_comparator import PeriodComparator
from backend.analytics.anomaly_detector import AnomalyDetector
from backend.analytics.trend_aggregator import TrendAggregator

router = APIRouter(prefix="/api/v2/insights", tags=["insights"])


@router.get("/vic-persona")
async def get_vic_persona():
    try:
        analyzer = VicPersonaAnalyzer()
        return await analyzer.analyze_vic_group()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VIC 群体画像查询失败: {str(e)}")


@router.get("/period-comparison")
async def get_period_comparison(
    start_date: date = Query(..., description="当期开始日期"),
    end_date: date = Query(..., description="当期结束日期"),
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date 不能大于 end_date")
    try:
        comparator = PeriodComparator()
        return await comparator.compare_metrics(start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"时间对比查询失败: {str(e)}")


@router.get("/anomaly-alerts")
async def get_anomaly_alerts():
    try:
        detector = AnomalyDetector()
        return await detector.get_all_anomalies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"异常客户检测失败: {str(e)}")


@router.get("/customer-trends")
async def get_customer_trends(months: int = Query(6, ge=1, le=24)):
    try:
        aggregator = TrendAggregator()
        return await aggregator.get_customer_trends(months)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"趋势数据查询失败: {str(e)}")
```

- [ ] **Step 3: 在 main.py 中注册路由**

读取 `backend/main.py`，在 `app.include_router()` 调用后追加：

```python
from backend.api.insights_routes import router as insights_router
app.include_router(insights_router)
```

- [ ] **Step 4: 启动后端 + 手动测试 + 自动化测试**

Run: `python -m backend.main &`
Run: `curl -s http://localhost:8000/api/v2/insights/vic-persona | python -m json.tool`
Run: `pytest tests/api/test_insights_routes.py -v`

Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add backend/api/insights_routes.py backend/main.py tests/api/test_insights_routes.py
git commit -m "feat(api): add 4 insights API endpoints"
```

---

### Task 9: Action API 路由（库存需求列表）

**Files:**
- Create: `backend/api/action_routes.py`
- Create: `tests/api/test_action_routes.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 编写测试**

Create `tests/api/test_action_routes.py`:

```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_inventory_inquiries():
    response = client.get("/api/v2/action/inventory-inquiries")
    assert response.status_code == 200
    data = response.json()
    assert "inquiries" in data
    assert "total_count" in data
```

- [ ] **Step 2: 实现 action_routes.py**

Create `backend/api/action_routes.py`:

```python
from fastapi import APIRouter, HTTPException
import json

router = APIRouter(prefix="/api/v2/action", tags=["action"])


@router.get("/inventory-inquiries")
async def get_inventory_inquiries():
    try:
        from backend.database.db_config import get_db_connection

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT
            tb.buyer_nick, tb.vip_level, tb.last_chat_date,
            ai.dominant_intent, ai.intent_distribution, ai.sentiment_label,
            (SELECT COUNT(*) FROM chat_history ch WHERE ch.buyer_nick = tb.buyer_nick) as total_chat_messages
        FROM target_buyers_precomputed tb
        JOIN buyer_ai_analysis_cache ai ON tb.buyer_nick = ai.buyer_nick
        WHERE ai.dominant_intent = 'Inventory Inquiry'
           OR JSON_EXTRACT(ai.intent_distribution, '$.\\"Inventory Inquiry\\"') > 0.3
        ORDER BY
            CASE tb.vip_level
                WHEN 'V3' THEN 1
                WHEN 'V2' THEN 2
                WHEN 'V1' THEN 3
                WHEN 'V0' THEN 4
                ELSE 5
            END ASC,
            tb.last_chat_date DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        inquiries = []
        for row in rows:
            intent_dist = row.get("intent_distribution")
            if isinstance(intent_dist, str):
                intent_dist = json.loads(intent_dist)
            inquiries.append({
                "buyer_nick": row["buyer_nick"],
                "vip_level": row.get("vip_level", "Non-VIP"),
                "dominant_intent": row.get("dominant_intent", "Unknown"),
                "intent_distribution": intent_dist or {},
                "sentiment_label": row.get("sentiment_label", "Neutral"),
                "last_chat_date": str(row["last_chat_date"]) if row.get("last_chat_date") else None,
                "total_chat_messages": row.get("total_chat_messages", 0),
            })

        return {"inquiries": inquiries, "total_count": len(inquiries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"库存需求查询失败: {str(e)}")
```

- [ ] **Step 3: 在 main.py 中注册 + 启动 + 测试**

读取 main.py 加入：

```python
from backend.api.action_routes import router as action_router
app.include_router(action_router)
```

Run: `python -m backend.main &`
Run: `curl -s http://localhost:8000/api/v2/action/inventory-inquiries | python -m json.tool`
Run: `pytest tests/api/test_action_routes.py -v`

- [ ] **Step 4: 提交**

```bash
git add backend/api/action_routes.py backend/main.py tests/api/test_action_routes.py
git commit -m "feat(api): add inventory inquiries endpoint"
```

---

### Task 10: 更新 Keyword Analysis 端点（加入第 10 类）

**Files:**
- Modify: `backend/api/target_routes.py`

- [ ] **Step 1: 读取现有端点**

Run: `grep -n "keyword-analysis" backend/api/target_routes.py`

- [ ] **Step 2: 在 keyword 聚合逻辑中加入 inventory_inquiry**

在 keyword 聚合代码块中追加：

```python
from backend.analytics.keyword_categories import INVENTORY_INQUIRY_KEYWORDS
import json
import re


def classify_inventory_inquiry(buyer_data: dict) -> bool:
    intent_dist = buyer_data.get("intent_distribution", {})
    if isinstance(intent_dist, str):
        intent_dist = json.loads(intent_dist)
    if intent_dist.get("Inventory Inquiry", 0) > 0.3:
        return True
    chat_messages = buyer_data.get("recent_chats", [])
    for msg in chat_messages:
        for pattern in INVENTORY_INQUIRY_KEYWORDS["patterns"]:
            if re.search(pattern, msg):
                return True
    return False


# 在聚合循环中调用
inventory_inquiry_buyers = []
for buyer in all_buyers:
    if classify_inventory_inquiry(buyer):
        inventory_inquiry_buyers.append(buyer)

categories.append({
    "name": "库存查询",
    "count": len(inventory_inquiry_buyers),
    "buyers": inventory_inquiry_buyers[:10],
})
```

- [ ] **Step 3: 手动测试端点**

Run: `curl -s "http://localhost:8000/api/v2/keyword-analysis?buyer_type=SMOKER" | python -m json.tool`

Expected: categories 数组包含 10 个元素

- [ ] **Step 4: 提交**

```bash
git add backend/api/target_routes.py
git commit -m "feat(api): integrate inventory_inquiry into keyword analysis"
```

---

### Task 11: 端到端 API 测试

**Files:**
- Create: `tests/integration/test_insights_e2e.py`

- [ ] **Step 1: 编写端到端测试**

Create `tests/integration/test_insights_e2e.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_dashboard_overview_apis_workflow():
    response = client.get("/api/v2/insights/vic-persona")
    assert response.status_code == 200
    vic_data = response.json()
    assert vic_data["total_vic_count"] >= 0

    response = client.get(
        "/api/v2/insights/period-comparison",
        params={"start_date": "2026-05-01", "end_date": "2026-05-31"},
    )
    assert response.status_code == 200
    comparison = response.json()
    assert "current_period" in comparison
    assert comparison["current_period"]["start_date"] == "2026-05-01"
    assert comparison["comparison_period"]["end_date"] == "2026-04-30"

    response = client.get("/api/v2/insights/anomaly-alerts")
    assert response.status_code == 200
    anomalies = response.json()
    assert "anomalies" in anomalies

    response = client.get("/api/v2/insights/customer-trends?months=6")
    assert response.status_code == 200
    trends = response.json()
    assert "vic_pool_trend" in trends

    response = client.get("/api/v2/action/inventory-inquiries")
    assert response.status_code == 200
    inventory = response.json()
    assert "inquiries" in inventory


def test_apis_return_consistent_data_types():
    response = client.get("/api/v2/insights/vic-persona")
    data = response.json()
    assert isinstance(data["total_vic_count"], int)
    assert isinstance(data["key_interests"], list)
    assert isinstance(data["key_pain_points"], list)
    if len(data["key_interests"]) > 0:
        first = data["key_interests"][0]
        assert isinstance(first["keyword"], str)
        assert isinstance(first["count"], int)
        assert isinstance(first["percentage"], (int, float))


def test_apis_performance_under_5s():
    import time

    start = time.time()
    endpoints = [
        "/api/v2/insights/vic-persona",
        "/api/v2/insights/period-comparison?start_date=2026-05-01&end_date=2026-05-31",
        "/api/v2/insights/anomaly-alerts",
        "/api/v2/insights/customer-trends?months=6",
        "/api/v2/action/inventory-inquiries",
    ]
    for url in endpoints:
        r = client.get(url)
        assert r.status_code == 200
    elapsed = time.time() - start
    print(f"5 APIs total: {elapsed:.2f}s")
    assert elapsed < 5.0
```

- [ ] **Step 2: 运行端到端测试**

Run: `pytest tests/integration/test_insights_e2e.py -v`

Expected: PASS

- [ ] **Step 3: 修复失败（如有）+ 提交**

```bash
git add tests/integration/test_insights_e2e.py
git commit -m "test(api): add end-to-end test for all 5 new APIs"
```

---

## Phase 2-3 后端完成

**所有 11 个任务完成后，Phase 2-3 后端开发结束。**

下一步：进入 Phase 4 前端开发（见 `docs/superpowers/plans/2026-06-14-overview-redesign-frontend.md`）。
