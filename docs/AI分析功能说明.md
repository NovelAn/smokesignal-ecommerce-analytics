# AI分析功能 - 实现文档

## 📅 完成时间
2026-01-20

## 🤖 功能概述

AI买家画像分析功能利用智谱AI（GLM-4）分析买家的历史数据和聊天记录，自动生成个性化的买家画像，包括兴趣点、痛点和销售建议。

---

## ✨ 核心功能

### 1. 智能买家画像生成

**输入数据：**
- ✅ 买家基本信息（昵称、城市、VIP等级）
- ✅ 消费数据（历史总额、订单数、近6个月数据）
- ✅ 标签信息（流失风险、折扣敏感度、偏好类别）
- ✅ 聊天记录（最近20条）

**输出内容：**
- 📝 **Summary**: 2-3句话的买家画像总结
- 🎯 **Key Interests**: 3-5个兴趣点
- ⚠️ **Pain Points**: 2-3个痛点
- 💡 **Recommended Action**: 具体的销售建议

### 2. 前端交互

**UI组件：**
- 🟣 **AI分析开关**: 位于买家详情页面右上角
  - 关闭状态：显示基础数据，不调用AI
  - 开启状态：调用AI API，生成智能分析
- ⏳ **加载提示**: 显示"AI正在分析买家画像..."
- ❌ **错误处理**: AI失败时显示友好提示

**视觉设计：**
- 紫色主题（AI感）
- Sparkles图标
- Toggle开关动画
- 区分AI生成数据和默认数据

---

## 🔧 技术实现

### 后端实现

#### 文件：`backend/api/target_routes.py`

**核心函数：** `_add_ai_analysis`

```python
async def _add_ai_analysis(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    添加AI生成的买家洞察

    功能：
    1. 获取买家最近20条聊天记录
    2. 准备订单摘要
    3. 调用Zhipu AI生成买家画像
    4. 返回分析结果
    """
    # 1. 获取聊天记录
    from backend.database import Database, BuyerQueries
    query, params = BuyerQueries.get_chat_messages(user_nick, limit=20)
    chats = db.execute_query(query, params)

    # 2. 准备订单摘要
    order_summary = f"""
    历史订单总数: {profile.get('total_orders', 0)}单
    历史消费总额: ¥{profile.get('historical_ltv', 0):.2f}
    近6个月消费: ¥{profile.get('l6m_spend', 0):.2f}
    ...
    """

    # 3. 调用Zhipu AI
    ai_analysis = ai_client.analyze_buyer_persona(
        user_nick=user_nick,
        profile_data=profile,
        recent_chats=chats,
        order_summary=order_summary
    )

    # 4. 添加到profile
    profile["ai_analysis"] = ai_analysis
    return profile
```

**API端点：**
```python
@router.get("/buyers/{user_nick}")
async def get_buyer_profile(
    user_nick: str,
    include_ai: bool = Query(False, description="是否包含AI分析")
):
    profile = analyzer.get_buyer_profile(user_nick)
    if include_ai:
        profile = await _add_ai_analysis(profile)
    return profile
```

### Zhipu AI集成

**文件：** `backend/ai/zhipu_client.py`

**核心方法：** `analyze_buyer_persona`

```python
def analyze_buyer_persona(
    self,
    user_nick: str,
    profile_data: Dict[str, Any],
    recent_chats: List[Dict[str, Any]],
    order_summary: str
) -> Dict[str, Any]:
    """
    使用智谱AI分析买家画像

    返回：
    {
        "summary": "买家画像总结",
        "key_interests": ["兴趣1", "兴趣2"],
        "pain_points": ["痛点1", "痛点2"],
        "recommended_action": "销售建议"
    }
    """
```

**AI Prompt结构：**
```markdown
请根据以下买家的数据，生成买家画像分析报告：

【基本信息】
昵称：{user_nick}
VIP等级：{vip_level}
流失风险：{churn_risk}

【消费数据】
历史订单总数：{total_orders}单
历史消费总额：¥{historical_ltv}
近6个月消费：¥{l6m_spend}

【近期沟通记录】（最近20条）
{聊天记录内容}

请生成以下分析（JSON格式）：
{
  "summary": "买家画像总结（2-3句话）",
  "key_interests": ["兴趣点1", "兴趣点2"],
  "pain_points": ["痛点1", "痛点2"],
  "recommended_action": "具体的销售建议"
}
```

### 前端实现

#### 文件：`src/App.tsx`

**状态管理：**
```typescript
const [enableAI, setEnableAI] = useState(false); // AI分析开关

// 获取买家详情（包含AI分析）
const { data: buyerProfile, isLoading: profileLoading } = useDataFetchingWithRetry(
  async () => {
    if (!currentSession?.user_nick) return null;
    return apiClient.getBuyerProfile(currentSession.user_nick, enableAI);
  },
  2,
  [currentSession?.user_nick, enableAI] // AI开关改变时重新获取
);
```

**UI组件：**
```tsx
{/* AI分析开关 */}
<div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 border border-purple-200 rounded-md">
  <Sparkles size={14} className="text-purple-600" />
  <label className="flex items-center gap-2 cursor-pointer">
    <span className="text-xs font-medium text-purple-900">AI分析</span>
    <button
      onClick={() => setEnableAI(!enableAI)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        enableAI ? 'bg-purple-600' : 'bg-purple-200'
      }`}
    >
      <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
        enableAI ? 'translate-x-5' : 'translate-x-1'
      }`} />
    </button>
  </label>
</div>
```

**AI分析展示：**
```tsx
<NotionCard icon={Sparkles} title="AI Persona Analysis">
  {profileLoading ? (
    <LoadingSpinner text="AI正在分析买家画像..." />
  ) : (
    <>
      {/* Summary */}
      <div className="bg-purple-50 p-4 rounded">
        "{enrichedProfile?.analysis?.summary}"
      </div>

      {/* Key Interests */}
      <div className="flex flex-wrap gap-2">
        {enrichedProfile?.analysis?.key_interests.map((tag, i) => (
          <span key={i} className="px-2.5 py-1 bg-blue-50 text-blue-700 rounded">
            {tag}
          </span>
        ))}
      </div>

      {/* Pain Points */}
      <div className="flex flex-wrap gap-2">
        {enrichedProfile?.analysis?.pain_points.map((tag, i) => (
          <span key={i} className="px-2.5 py-1 bg-red-50 text-red-700 rounded">
            {tag}
          </span>
        ))}
      </div>

      {/* Recommended Action */}
      <div className="bg-yellow-50 p-3 rounded">
        {enrichedProfile?.analysis?.recommended_action}
      </div>
    </>
  )}
</NotionCard>
```

---

## 📊 数据流

### 1. 用户启用AI分析

```
用户点击"AI分析"开关
    ↓
enableAI = true
    ↓
重新调用 apiClient.getBuyerProfile(userNick, true)
    ↓
后端收到 include_ai=true
```

### 2. 后端处理流程

```
GET /api/v2/buyers/{user_nick}?include_ai=true
    ↓
获取基本信息（从预计算表，< 0.1秒）
    ↓
调用 _add_ai_analysis(profile)
    ↓
    ├─ 获取聊天记录（最近20条）
    ├─ 准备订单摘要
    ├─ 调用 Zhipu AI.analyze_buyer_persona()
    │   ├─ 构建Prompt
    │   ├─ 调用GLM-4 API
    │   └─ 解析JSON响应
    └─ 添加 ai_analysis 到 profile
    ↓
返回完整profile（包含AI分析）
```

### 3. 前端展示

```
收到 buyerProfile 数据
    ↓
profileLoading = false
    ↓
合并到 enrichedProfile
    ↓
展示AI分析结果
    ├─ Summary（紫色背景）
    ├─ Key Interests（蓝色标签）
    ├─ Pain Points（红色标签）
    └─ Recommended Action（黄色背景）
```

---

## 🎯 使用场景

### 场景1：客服查看买家详情

**操作流程：**
1. 在"Chat & CRM"页面搜索并选择买家
2. 点击"AI分析"开关
3. 等待3-10秒（显示加载动画）
4. 查看AI生成的买家画像

**AI输出示例：**
```json
{
  "summary": "高价值VIP客户，偏好高端烟斗配件。对新品上架和库存情况高度关注，习惯提前预订限量款。价格敏感度低，更注重产品品质和 exclusivity。",
  "key_interests": [
    "限量款新品",
    "高端配件升级",
    "会员专属权益"
  ],
  "pain_points": [
    "热销款经常断货",
    "新品通知不及时"
  ],
  "recommended_action": "主动推送新品上架通知，提供限量款预订服务，强调会员优先购买权。"
}
```

### 场景2：销售制定跟进策略

**应用：**
- 根据AI识别的痛点定制话术
- 基于兴趣点推荐相关产品
- 参考Recommended Action制定跟进计划

---

## ⚙️ 配置要求

### 1. 环境变量

**文件：** `backend/.env`

```bash
# Zhipu AI配置
ZHIPU_API_KEY=your_api_key_here
ZHIPU_MODEL=glm-4-plus
```

### 2. 数据库要求

**需要的表：**
- ✅ `target_buyers_precomputed` - 买家基本信息（已实现）
- ✅ `chat_history` - 聊天记录（已存在）

---

## ⚡ 性能优化

### 1. 异步处理
- AI分析使用 `async/await`，不阻塞其他请求
- 前端显示加载状态，用户体验友好

### 2. 按需调用
- 默认不启用AI分析（enableAI = false）
- 仅在用户需要时调用（节省API费用）

### 3. 错误降级
- AI失败不影响基本信息展示
- 显示默认提示："建议根据买家历史购买情况制定个性化跟进方案"

---

## 🐛 常见问题

### 问题1：AI分析返回错误

**可能原因：**
- ZHIPU_API_KEY未配置或无效
- 网络连接问题
- API限流

**解决方案：**
```bash
# 检查环境变量
echo $ZHIPU_API_KEY

# 测试API连接
python -c "from backend.ai import ZhipuClient; client = ZhipuClient(); print(client.client)"
```

### 问题2：AI分析速度慢

**原因：**
- AI API调用需要3-10秒
- 聊天记录多时处理时间更长

**优化：**
- 减少聊天记录数量（limit=20）
- 使用更快的模型（glm-4-air）
- 考虑缓存AI结果

### 问题3：AI分析结果不准确

**原因：**
- 聊天记录太少或质量差
- Prompt不够优化

**改进：**
- 增加更多上下文数据（订单历史、产品偏好）
- 优化Prompt模板
- 使用Few-shot示例

---

## 📈 后续改进方向

### 短期（1-2周）
- [ ] 添加AI分析缓存（Redis）
- [ ] 支持批量AI分析（多个买家）
- [ ] 添加AI分析历史记录

### 中期（1个月）
- [ ] 优化Prompt，提高准确率
- [ ] 支持自定义AI分析维度
- [ ] 添加AI分析对比功能

### 长期（3个月）
- [ ] 训练专属模型（Fine-tuning）
- [ ] 实时AI分析（WebSocket）
- [ ] AI分析报告导出（PDF）

---

## 📝 总结

AI分析功能成功集成，主要特点：

✅ **智能**: 基于真实数据生成个性化买家画像
✅ **高效**: 3-10秒生成完整分析
✅ **友好**: 清晰的UI，按需使用
✅ **可靠**: 错误处理完善，降级方案合理

**下一步：** 测试功能，收集反馈，持续优化。
