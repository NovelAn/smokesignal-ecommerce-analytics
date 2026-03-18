---
category: 功能文档
title: AI客户画像分析功能
tags: ['AI', 'DeepSeek', 'Zhipu', '客户洞察', '画像分析', 'Fallback', '缓存']
description: 使用DeepSeek和智谱GLM-4.7进行深度客户画像分析，支持多级降级策略和智能缓存
priority: high
last_updated: 2026-02-24
---

# AI客户画像分析功能

**最后更新：** 2026-02-24
**当前版本：** v3.0
**状态：** ✅ 生产就绪

---

## 📋 功能概述

AI客户画像分析使用DeepSeek-V3.2（主模型）和智谱GLM-4.7（备选模型），基于客户的历史消费数据、订单信息和聊天记录，生成深度的客户洞察报告。

### v3.0 新增功能

- **多级降级策略**: DeepSeek → GLM-4.7 → 规则引擎
- **429错误自动降级**: API余额不足时自动切换备选模型
- **智能缓存机制**: MySQL缓存 + 动态TTL，降低80%+成本
- **缓存验证**: 避免缓存失败的AI分析结果

### 核心能力

- **深度画像总结** - 分析购买决策模式、价值取向、消费心理特征
- **隐性兴趣点挖掘** - 推断生活方式、价值观、潜在需求
- **潜在痛点识别** - 基于行为数据推断未被满足的需求或担忧
- **个性化跟进策略** - 生成具体的、可执行的销售建议

### vs 传统数据分析

| 传统数据报表 | AI画像分析 |
|-------------|-----------|
| 历史消费6500元 | 目标明确的高价值新客户，首次购买即选择高客单价产品 |
| 来自北京 | 专业级产品收藏，追求品质体验 |
| 购买PIPES | 注重产品工艺与材质，愿意为品质支付溢价 |
| 无 | 需要专业产品使用指导，对品质有潜在疑虑 |

---

## 🏗️ 技术架构

### 多级降级策略

```
┌─────────────────────────────────────────────────────────────┐
│                    AI分析请求                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 检查缓存                                            │
│  MySQL ai_analysis_cache 表                                  │
│  • 缓存命中 → 直接返回 (< 0.1秒)                             │
│  • 缓存未命中 → 继续AI分析                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L1: DeepSeek-V3.2 (主模型)                                  │
│  ├─ 有聊天记录 → deepseek-reasoner (深度推理)                │
│  └─ 无聊天记录 → deepseek-chat (快速分析)                    │
│                                                             │
│  降级条件: 429错误(余额不足)、Timeout、API异常               │
└─────────────────────────────────────────────────────────────┘
                              │ 降级
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L2: Zhipu GLM-4.7 (备选模型 - Fallback)                    │
│  • 月卡订阅，无单次调用成本                                  │
│  • 基于消费数据分析                                          │
└─────────────────────────────────────────────────────────────┘
                              │ 降级
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L3: 规则引擎 (兜底)                                         │
│  • 零成本，100%可用                                         │
└─────────────────────────────────────────────────────────────┘
```

### 系统组件

```
Frontend (React)
    ↓ API Call
Backend API (FastAPI)
    ↓ Cache Check
MySQL Cache (ai_analysis_cache)
    ↓ Cache Miss
Analyzer Orchestrator
    ├─ DeepSeek Client (L1 - 主模型)
    ├─ Zhipu Client (L2 - 备选模型)
    └─ Rule-Based Engine (L3 - 兜底)
    ↓ AI Processing
Customer Persona Response
    ↓ Cache Result + JSON Parsing
Frontend Display
```

### 核心文件

| 文件 | 职责 |
|------|------|
| `backend/ai/analyzer_orchestrator.py` | 多级降级策略编排 |
| `backend/ai/deepseek_client.py` | DeepSeek AI客户端（主模型） |
| `backend/ai/zhipu_client.py` | Zhipu AI客户端（备选模型） |
| `backend/ai/cache_manager.py` | MySQL缓存管理 |
| `backend/ai/cache_strategy.py` | 动态TTL策略 |
| `backend/api/target_routes.py` | API端点和数据准备 |
| `src/App.tsx` | 前端AI分析开关和结果展示 |
| `backend/config.py` | API密钥配置 |

---

## 🔧 配置指南

### 1. 环境变量配置

在项目根目录创建 `.env` 文件：

```bash
# ===== DeepSeek AI Configuration (推荐 - 主要分析模型) =====
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_MODEL_R1=deepseek-reasoner
DEEPSEEK_MODEL_CHAT=deepseek-chat
DEEPSEEK_MODEL=DeepSeek-V3.2
DEEPSEEK_TEMP_EVIDENCE=0.3
DEEPSEEK_TEMP_INFERENCE=0.7

# ===== Zhipu AI Configuration (备选模型 - Fallback) =====
# 当DeepSeek API余额不足(429)或超时时，自动降级到此模型
ZHIPU_API_KEY=xxxxxxxx
ZHIPU_MODEL=glm-4-plus  # GLM-4.7 备选模型

# AI Analysis Configuration
AI_CACHE_TTL_DAYS=30
AI_ENABLE_CACHE=true
```

### 2. 获取API密钥

**DeepSeek AI**:
1. 访问 [DeepSeek开放平台](https://platform.deepseek.com/)
2. 注册账号并登录
3. 进入API密钥管理页面
4. 创建新的API密钥
5. 将密钥添加到 `.env` 文件

**智谱AI (备选)**:
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册账号并登录
3. 进入API密钥管理页面
4. 创建新的API密钥
5. 将密钥添加到 `.env` 文件

### 3. 模型选择策略

| 场景 | 模型选择 | 原因 |
|------|----------|------|
| 有聊天记录 | DeepSeek-R1 | 深度推理，文本分析能力强 |
| 无聊天记录 | DeepSeek-Chat | 快速分析，成本较低 |
| DeepSeek失败 | Zhipu GLM-4.7 | 备选模型，月卡无单次成本 |
| 所有AI失败 | 规则引擎 | 兜底方案，零成本 |

---

## 📊 数据准备

### 输入数据结构

AI分析需要以下三类数据：

#### 1. 基本信息
```json
{
  "user_nick": "mylifemyrule",
  "city": "北京",
  "vip_level": "Non-VIP",
  "client_monthly_tag": "new"
}
```

#### 2. 消费行为数据
```json
{
  "historical_net_sales": 6500.00,
  "total_orders": 1,
  "l6m_spend": 6500.00,
  "l6m_orders": 1,
  "refund_rate": 0.0,
  "discount_sensitivity": "低",
  "churn_risk": "低"
}
```

#### 3. 产品偏好
```json
{
  "top_category": "PIPES",
  "second_category": "N/A",
  "third_category": "N/A"
}
```

#### 4. 聊天记录
```json
[
  {
    "sender_nick": "mylifemyrule",
    "content": "这个图是实物拍的么",
    "msg_time": "2026-01-19T18:50:59"
  },
  {
    "sender_nick": "dunhill登喜路官方旗舰店:lei",
    "content": "在的",
    "msg_time": "2026-01-19T18:50:34"
  }
]
```

---

## 🎯 提示词工程

### 提示词设计原则

#### 1. 明确禁止简单重复
```
❌ 不要说："来自XX的客户，消费了XX元"
✅ 要分析：购买决策模式、价值取向、消费心理特征
```

#### 2. 提供具体示例
```
例如："这是一位注重品质胜过价格的务实型买家，
首次购买即选择高价位PIPES产品，显示出明确的目标性
和较强的支付意愿。"
```

#### 3. 强调推断而非描述
```
❌ 不要："来自北京"、"喜欢PIPES"
✅ 要推断：生活方式、价值观、潜在需求
```

### 提示词结构

```python
prompt = f"""
你是一位资深电商客户洞察专家。请基于以下数据进行深度买家画像分析，**不要简单重复数据**，而是要挖掘背后的行为模式、心理动机和潜在需求。

【买家数据】
{order_summary}

【聊天记录】（最近{len(chats)}条）
{formatted_chats}

**分析要求：**

1. **summary** - 深度画像总结（2-3句话）
   ❌ 不要说："来自XX的客户，消费了XX元"
   ✅ 要分析：购买决策模式、价值取向、消费心理特征

2. **key_interests** - 隐性兴趣点（3-5个）
   ❌ 不要："来自北京"、"喜欢PIPES"
   ✅ 要推断：生活方式、价值观、潜在需求

3. **pain_points** - 潜在痛点（2-4个）
   基于消费行为和聊天内容推断未被满足的需求或担忧

4. **recommended_action** - 个性化跟进策略（1-2句话）
   具体的、可执行的、针对该买家的独特建议

**输出格式（纯JSON，不要其他文字）：**
{{
  "summary": "深度画像总结...",
  "key_interests": ["推断的兴趣点1", "兴趣点2", "兴趣点3"],
  "pain_points": ["推断的痛点1", "痛点2"],
  "recommended_action": "个性化建议..."
}}
"""
```

---

## 🚀 API使用

### 端点

```http
GET /api/v2/buyers/{user_nick}?include_ai=true
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_nick | string | 是 | 买家昵称 |
| include_ai | boolean | 否 | 是否包含AI分析（默认false） |

### 响应示例

```json
{
  "user_nick": "mylifemyrule",
  "city": "北京",
  "historical_net_sales": 6500.00,
  "total_orders": 1,
  "ai_analysis": {
    "summary": "这是一位目标明确的高价值新客户，首次购买即选择高客单价PIPES产品，显示出对特定品类有深入研究且决策果断，属于品质导向型消费者而非价格敏感型。",
    "key_interests": [
      "专业级PIPES产品收藏或使用",
      "追求高品质生活体验",
      "注重产品工艺与材质",
      "可能具备相关专业知识或正在培养专业兴趣",
      "愿意为独特价值支付溢价"
    ],
    "pain_points": [
      "可能需要专业产品使用指导与维护建议",
      "对产品真伪鉴别和品质保障存在顾虑",
      "缺乏同类产品对比信息和专业评价"
    ],
    "recommended_action": "提供PIPES产品的专业使用指南、保养技巧和材质鉴别知识，同时分享品牌故事和工艺细节，强化专业形象并建立长期信任关系。"
  }
}
```

---

## 💻 前端集成

### 1. 启用AI分析开关

```typescript
const [enableAI, setEnableAI] = useState(false);

<Switch
  checked={enableAI}
  onCheckedChange={setEnableAI}
  label="AI分析"
/>
```

### 2. 获取客户画像

```typescript
const { data: buyerProfile } = useDataFetchingWithRetry(
  async () => {
    if (!currentSession?.user_nick) return null;
    const includeAI = enableAI; // 根据开关决定是否启用AI
    return await apiClient.getBuyerProfile(currentSession.user_nick, includeAI);
  },
  2,
  [currentSession?.user_nick, enableAI]
);
```

### 3. 展示AI分析结果

```typescript
{buyerProfile?.ai_analysis && (
  <div className="ai-analysis-card">
    <h3>AI Persona Analysis</h3>
    <p>{buyerProfile.ai_analysis.summary}</p>

    <h4>Key Interests</h4>
    <ul>
      {buyerProfile.ai_analysis.key_interests.map((interest, idx) => (
        <li key={idx}>{interest}</li>
      ))}
    </ul>

    <h4>Pain Points</h4>
    <ul>
      {buyerProfile.ai_analysis.pain_points.map((point, idx) => (
        <li key={idx}>{point}</li>
      ))}
    </ul>

    <h4>Recommended Action</h4>
    <p>{buyerProfile.ai_analysis.recommended_action}</p>
  </div>
)}
```

---

## 📈 性能优化

### 当前性能

| 指标 | 缓存命中 | 缓存未命中 |
|------|----------|------------|
| AI分析响应时间 | < 0.1秒 | 60-90秒 |
| API数据准备 | < 0.1秒 | < 0.1秒 |
| 前端渲染 | < 0.5秒 | < 0.5秒 |
| 总体用户体验 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

### 智能缓存机制

#### 缓存策略

| VIP等级 | 缓存TTL | 原因 |
|---------|---------|------|
| V3/V2 (高价值) | 7天 | 数据变化快，需要更频繁更新 |
| V1/有聊天记录 | 14天 | 行为可能变化 |
| Non-VIP/无聊天 | 30天 | 消费数据稳定 |

#### 缓存验证

为避免缓存失败的AI分析结果，实现了缓存验证机制：

```python
def _is_valid_analysis_result(self, result: Dict) -> bool:
    """验证AI分析结果是否有效（不缓存失败结果）"""
    if not result:
        return False

    # 必须包含关键字段
    required_fields = ['summary', 'key_interests', 'pain_points', 'recommended_action']
    for field in required_fields:
        if field not in result:
            return False

    # 检查是否是默认/失败响应
    summary = result.get('summary', '')
    if not summary or '暂无AI分析' in summary or 'AI分析失败' in summary:
        return False

    return True
```

#### 缓存命中示例

```json
{
  "ai_analysis": {
    "summary": "客户专注PIPES品类...",
    "cache_status": "HIT",
    "cached_at": "2026-02-20T10:30:00",
    "expires_at": "2026-03-07T00:00:00"
  }
}
```

### 成本优化

| 模型 | 计费方式 | 单次成本 | 适用场景 |
|------|----------|----------|----------|
| DeepSeek-R1 | 按Token计费 | ~¥7/次 | 深度推理，有聊天记录 |
| DeepSeek-Chat | 按Token计费 | ~¥3/次 | 快速分析 |
| Zhipu GLM-4.7 | 月卡订阅 | ¥0/次 | 备选模型 |
| 规则引擎 | 免费 | ¥0/次 | 兜底方案 |

**优化效果**:
- 优化前月度成本: ~¥21,000
- 优化后月度成本: ~¥2,500
- **节省: 88%↓** 🎉

### 优化建议

1. **并行处理** - AI分析可异步进行，不阻塞基本信息展示
2. **缓存预热** - 预先分析高价值客户，提高缓存命中率
3. **批量分析** - 支持一次分析多个客户，降低API调用成本
4. **模型选择** - 根据场景选择合适的模型（速度 vs 质量）

---

## 🔍 故障排查

### 问题1：AI分析返回错误

**症状**：`ai_analysis` 字段显示错误信息

**可能原因**：
- API密钥未配置或已过期
- 网络连接问题
- API配额已用完（429错误）

**解决方案**：
```bash
# 检查DeepSeek API密钥
cat .env | grep DEEPSEEK_API_KEY

# 检查Zhipu API密钥（备选模型）
cat .env | grep ZHIPU_API_KEY

# 测试API连接
python -c "from backend.ai import ZhipuClient; client = ZhipuClient(); print('OK')"
```

### 问题2：AI分析自动降级到备选模型

**症状**：日志显示 `[L1→L2] DeepSeek API余额不足(429)，降级到Zhipu GLM-4.7`

**可能原因**：
- DeepSeek API余额不足
- DeepSeek API超时
- DeepSeek API其他异常

**解决方案**：
1. 检查DeepSeek账户余额，及时充值
2. 检查网络连接是否稳定
3. 系统会自动降级到Zhipu GLM-4.7，不影响功能使用

### 问题3：AI分析质量差

**症状**：AI仅重复已有数据，未提供深度洞察

**可能原因**：
- 输入数据不完整（缺少聊天记录）
- 提示词被意外修改
- 模型选择不当

**解决方案**：
```python
# 检查聊天记录是否获取
query, params = BuyerQueries.get_chat_messages(user_nick, limit=20)
chats = db.execute_query(query, params)
print(f"Found {len(chats)} chat messages")

# 验证提示词完整性
grep "不要简单重复数据" backend/ai/zhipu_client.py
```

### 问题4：缓存未生效

**症状**：每次请求都调用AI模型，响应时间长

**可能原因**：
- 缓存功能未启用
- 缓存已过期
- 缓存验证失败

**解决方案**：
```bash
# 检查缓存配置
cat .env | grep AI_ENABLE_CACHE

# 检查数据库缓存表
mysql> SELECT buyer_nick, model_used, status, expires_at FROM ai_analysis_cache WHERE status = 'VALID';

# 手动清除缓存（测试用）
POST /api/v2/buyers/{user_nick}/invalidate-cache
```

### 问题5：字段显示为0

**症状**：AI分析显示"历史消费总额为0"

**可能原因**：
- 字段名不匹配（`historical_net_sales` vs `historical_ltv`）
- 数据源返回null

**解决方案**：
```python
# 已修复：使用回退机制
historical_ltv = float(profile.get('historical_net_sales', profile.get('historical_ltv', 0)))
```

---

## 📚 相关文档

- [智谱AI官方文档](https://open.bigmodel.cn/dev/api)
- [GLM-4模型介绍](https://open.bigmodel.cn/dev/model)
- [提示词工程最佳实践](../开发指南/提示词工程指南.md)

---

## 🎉 最佳实践

### 1. 数据质量优先

确保输入数据完整准确：
- ✅ 至少包含最近20条聊天记录
- ✅ 完整的消费历史数据
- ✅ 准确的产品分类信息

### 2. 合理使用AI

- ✅ 针对高价值客户使用AI分析
- ✅ 定期更新AI分析（每周/每月）
- ❌ 避免对所有客户批量分析（成本高）

### 3. 结合人工判断

- ✅ AI分析作为参考，人工最终决策
- ✅ 定期review AI分析质量
- ✅ 收集用户反馈优化提示词

---

## 🚀 未来增强

### 计划功能

- [x] 多级降级策略 - DeepSeek → GLM-4.7 → 规则引擎 ✅
- [x] 智能缓存机制 - MySQL缓存 + 动态TTL ✅
- [x] 429错误自动降级 - API余额不足时自动切换 ✅
- [ ] 异步处理 - AI分析异步任务队列
- [ ] 批量AI分析 - 一次分析多个客户
- [ ] AI对比分析 - 对比不同客户群体
- [ ] AI趋势预测 - 预测客户未来行为
- [ ] AI报告生成 - 自动生成周报/月报
- [ ] 自定义提示词 - 允许用户修改分析维度
- [ ] 成本监控 - 实时追踪API使用和成本

---

## 📚 相关文档

- [AI分析系统优化总结](../plans/2026-02-24-ai-optimization-summary.md)
- [AI分析优化计划](../plans/2026-02-03-ai-analysis-optimization-plan.md)
- [智谱AI官方文档](https://open.bigmodel.cn/dev/api)
- [DeepSeek官方文档](https://platform.deepseek.com/docs)
- [GLM-4模型介绍](https://open.bigmodel.cn/dev/model)
- [提示词工程最佳实践](../开发指南/提示词工程指南.md)

---

**最后更新：** 2026-02-24
**维护者：** SmokeSignal团队
