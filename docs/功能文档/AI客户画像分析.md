---
category: 功能文档
title: AI客户画像分析功能
tags: ['AI', 'Zhipu', '客户洞察', '画像分析']
description: 使用智谱GLM-4进行深度客户画像分析的技术文档
priority: high
last_updated: 2025-01-20
---

# AI客户画像分析功能

**最后更新：** 2025-01-20
**当前版本：** v2.1
**状态：** ✅ 生产就绪

---

## 📋 功能概述

AI客户画像分析使用智谱AI的GLM-4模型，基于客户的历史消费数据、订单信息和聊天记录，生成深度的客户洞察报告。

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

### 系统组件

```
Frontend (React)
    ↓ API Call
Backend API (FastAPI)
    ↓ Data Preparation
Zhipu AI Client (GLM-4)
    ↓ AI Processing
Customer Persona Response
    ↓ JSON Parsing
Frontend Display
```

### 核心文件

| 文件 | 职责 |
|------|------|
| `backend/ai/zhipu_client.py` | AI客户端封装和提示词工程 |
| `backend/api/target_routes.py` | API端点和数据准备 |
| `src/App.tsx` | 前端AI分析开关和结果展示 |
| `backend/config.py` | API密钥配置 |

---

## 🔧 配置指南

### 1. 环境变量配置

在项目根目录创建 `.env` 文件：

```bash
# 智谱AI配置
ZHIPU_API_KEY=your_api_key_here
ZHIPU_MODEL=glm-4-flash
```

### 2. 获取API密钥

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册账号并登录
3. 进入API密钥管理页面
4. 创建新的API密钥
5. 将密钥添加到 `.env` 文件

### 3. 模型选择

推荐模型：
- `glm-4-flash` - 快速响应，适合实时分析（推荐）
- `glm-4-air` - 平衡性能和成本
- `glm-4` - 最高质量，成本较高

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

| 指标 | 数值 |
|------|------|
| AI分析响应时间 | 3-10秒 |
| API数据准备 | < 0.1秒 |
| 前端渲染 | < 0.5秒 |
| 总体用户体验 | 可接受（显示loading） |

### 优化建议

1. **并行处理** - AI分析可异步进行，不阻塞基本信息展示
2. **缓存策略** - 对相同客户的AI分析结果缓存24小时
3. **批量分析** - 支持一次分析多个客户，降低API调用成本
4. **模型选择** - 根据场景选择合适的模型（速度 vs 质量）

---

## 🔍 故障排查

### 问题1：AI分析返回错误

**症状**：`ai_analysis` 字段显示错误信息

**可能原因**：
- API密钥未配置或已过期
- 网络连接问题
- API配额已用完

**解决方案**：
```bash
# 检查API密钥
cat .env | grep ZHIPU_API_KEY

# 测试API连接
python -c "from backend.ai import ZhipuClient; client = ZhipuClient(); print('OK')"
```

### 问题2：AI分析质量差

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

### 问题3：字段显示为0

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

- [ ] 批量AI分析 - 一次分析多个客户
- [ ] AI对比分析 - 对比不同客户群体
- [ ] AI趋势预测 - 预测客户未来行为
- [ ] AI报告生成 - 自动生成周报/月报
- [ ] 自定义提示词 - 允许用户修改分析维度

---

**最后更新：** 2025-01-20
**维护者：** SmokeSignal团队
