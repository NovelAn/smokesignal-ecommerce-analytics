---
category: 开发指南
title: 快速启动指南
tags: ['快速开始', '上下文恢复', '开发流程']
description: 快速恢复项目开发上下文和启动开发环境
priority: high
last_updated: 2026-02-27
---
# SmokeSignal Analytics - 快速启动指南

**最后更新：** 2026-02-27
**当前版本：** v2.3
**当前分支：** `feature/sql-field-names-update`

---

## 当前项目状态

### 已完成功能（v2.0 - v2.3）

1. **目标买家预计算系统**

   - 40-120x性能提升
   - 391个目标买家识别
   - 每日14:00自动刷新
2. **多模型AI分析系统（v2.2新增）** ⭐

   - L1: DeepSeek-V3.2（主模型 - 深度推理）
   - L2: Zhipu GLM-4.7（备选模型 - 降级）
   - L3: 规则引擎（兜底）
   - 429错误/超时自动降级
   - 88%成本优化
3. **AI缓存系统（v2.2新增）** ⭐

   - MySQL缓存存储
   - 动态TTL（7-30天）
   - 120-180x缓存命中性能提升
4. **情感/意图分析系统（v2.3新增）** ⭐

   - 批量分析客户情感（正面/中性/负面）
   - 识别客户意图（售前/售后/投诉等）
   - 前端一键触发批量分析
   - 增量更新策略（只分析有新聊天的客户）
5. **前端三大模块**

   - Dashboard Overview - 实时指标和可操作客户列表
   - Chat & CRM - 360°客户画像、AI分析、订单历史、聊天记录
   - Configuration - 管道状态和配置
5. **数据导出**

   - Excel客户数据导出
   - Rolling 24 Month指标显示

### 技术栈

- **前端**: React 19.2.3 + TypeScript + Vite 6.2.0 + Recharts 3.6.0
- **后端**: FastAPI + Python
- **AI**: DeepSeek-V3.2（主）+ Zhipu GLM-4.7（备）
- **数据库**: MySQL (阿里云RDS)
- **测试**: Playwright MCP (端到端测试)

---

## 快速启动

### 1. 启动后端服务

```bash
# Windows
scripts\start-backend.bat

# Linux/Mac
./scripts/start-backend.sh

# 或直接运行
python -m backend.main
```

**后端运行在**: `http://localhost:8000`

### 2. 启动前端服务

```bash
npm run dev
```

**前端运行在**: `http://localhost:3000`

### 3. 验证服务状态

```bash
# 检查后端API
curl http://localhost:8000/api/v2/

# 应该返回：
# {
#   "status": "ok",
#   "service": "SmokeSignal Analytics API v2 (Optimized)",
#   "version": "2.0.0",
#   "performance": "Using precomputed table - 10-50x faster"
# }
```

---

## 开发环境配置

### 必需的环境变量

创建 `.env` 文件：

```bash
# 数据库配置
DB_CONFIG_FILE=~/database_config.json
DB_NAME_TO_USE=aliyunDB

# DeepSeek AI 配置（主模型 - 推荐）
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_MODEL_R1=deepseek-reasoner
DEEPSEEK_MODEL_CHAT=deepseek-chat
DEEPSEEK_MODEL=DeepSeek-V3.2
DEEPSEEK_TEMP_EVIDENCE=0.3
DEEPSEEK_TEMP_INFERENCE=0.7

# 智谱AI 配置（备选模型 - Fallback）
# 当DeepSeek API余额不足(429)或超时时，自动降级到此模型
ZHIPU_API_KEY=xxxxxxxx
ZHIPU_MODEL=glm-4-plus  # GLM-4.7

# AI 分析配置
AI_CACHE_TTL_DAYS=30
AI_ENABLE_CACHE=true
```

### 获取API密钥

1. **DeepSeek AI** (主模型)

   - 访问 [DeepSeek开放平台](https://platform.deepseek.com/)
   - 注册并获取API密钥
2. **智谱AI** (备选模型)

   - 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
   - 注册并获取API密钥

---

## 项目结构速览

```
smokesignal-ecommerce-analytics/
├── backend/                      # Python后端
│   ├── ai/                      # AI客户端
│   │   ├── analyzer_orchestrator.py  # 多模型编排（v2.2核心）
│   │   ├── deepseek_client.py        # DeepSeek客户端
│   │   ├── zhipu_client.py           # 智谱AI客户端
│   │   ├── rule_based_analyzer.py    # 规则引擎
│   │   └── cache_manager.py          # AI缓存管理
│   ├── analytics/               # 数据分析
│   │   └── target_buyer_analyzer.py  # 目标买家分析器
│   ├── api/                     # API路由
│   │   └── target_routes.py     # v2 API路由
│   ├── database/                # 数据库层
│   │   ├── sql/                 # SQL查询文件
│   │   └── target_buyer_queries.py
│   └── main.py                  # FastAPI应用入口
│
├── src/                         # React前端
│   ├── api/                     # API客户端封装
│   ├── components/              # React组件
│   ├── hooks/                   # 自定义Hooks
│   └── App.tsx                  # 主应用
│
├── docs/                        # 文档
│   ├── 功能文档/                # 功能详细说明
│   │   └── AI客户画像分析.md    # AI功能文档（v3.0）
│   ├── plans/                   # 优化计划
│   │   └── 2026-02-24-ai-optimization-summary.md  # AI优化总结
│   ├── 项目记录/                # 项目进度
│   └── 架构设计/                # 架构文档
│
├── scripts/                     # 工具脚本
│   └── start-backend.bat        # 后端启动脚本（Windows）
│
└── tests/                       # 测试文件
```

---

## AI分析系统架构（v2.2核心功能）

### 多级降级策略

```
┌─────────────────────────────────────────────────────────────┐
│  L1: DeepSeek-V3.2 (主模型 - 推荐)                           │
│  ├─ 有聊天记录 → deepseek-reasoner (深度推理)                │
│  └─ 无聊天记录 → deepseek-chat (快速分析)                    │
│                                                             │
│  触发降级条件:                                               │
│  • 429错误 (API余额不足)                                     │
│  • Timeout超时                                              │
│  • 其他API异常                                              │
└─────────────────────────────────────────────────────────────┘
                              │ 降级
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L2: Zhipu GLM-4.7 (备选模型 - Fallback)                    │
│  • 当DeepSeek不可用时自动切换                                │
│  • 月卡订阅，无单次调用成本                                  │
└─────────────────────────────────────────────────────────────┘
                              │ 降级
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L3: 规则引擎 (兜底)                                         │
│  • 所有AI模型失败时使用                                      │
│  • 零成本，100%可用                                         │
└─────────────────────────────────────────────────────────────┘
```

### AI缓存动态TTL

| VIP等级        | 缓存TTL | 原因         |
| -------------- | ------- | ------------ |
| V3/V2 (高价值) | 7天     | 数据变化快   |
| V1/有聊天记录  | 14天    | 行为可能变化 |
| Non-VIP/无聊天 | 30天    | 消费数据稳定 |

### 成本优化效果

- **优化前**: ¥21,000/月 (100% DeepSeek-R1)
- **优化后**: ~¥2,500/月 (混合策略 + 缓存)
- **节省**: **¥18,500/月 (88%↓)**

---

## AI情感/意图分析

### 功能说明

系统可以批量分析客户的情感（正面/中性/负面）和意图（售前咨询/售后支持/物流/投诉等），帮助运营团队：

- 识别需要优先跟进的客户
- 发现潜在的投诉风险
- 跟踪售前转化机会
- 召回流失客户

**分析前提条件**：客户发送的消息数 >= 5 条（排除客服自动回复）

### 方式1: 前端按钮触发（推荐）

1. 启动前端服务：`npm run dev`
2. 访问 http://localhost:3000
3. 点击左侧菜单 **Configuration**
4. 在 **AI Analysis** 区域点击 **Start Batch Analysis** 按钮
5. 等待分析完成（会显示进度条）

分析完成后，可以看到情感分布统计（正面/中性/负面比例）。

### 方式2: API直接调用

```bash
# 启动批量分析（最多分析200个客户）
curl -X POST "http://localhost:8000/api/v2/ai/batch-analyze?buyer_limit=200"

# 返回示例
{
  "task_id": "task_20260227_123456",
  "status": "pending",
  "message": "批量分析任务已创建，将分析最多 200 个客户"
}

# 查询任务进度
curl "http://localhost:8000/api/v2/ai/batch-status/task_20260227_123456"

# 返回示例
{
  "task_id": "task_20260227_123456",
  "status": "running",
  "total_buyers": 50,
  "processed_buyers": 23,
  "progress_percent": 46,
  "started_at": "2026-02-27T10:00:00"
}

# 查看情感分析汇总
curl "http://localhost:8000/api/v2/analytics/sentiment-summary"

# 查看意图分析汇总
curl "http://localhost:8000/api/v2/analytics/intent-summary"
```

### 单个客户强制刷新

```bash
# 强制刷新单个客户的情感/意图分析
curl -X POST "http://localhost:8000/api/v2/buyers/客户昵称/force-refresh?refresh_type=sentiment"

# refresh_type 可选值：
# - "persona": 仅刷新客户画像
# - "sentiment": 仅刷新情感/意图分析
# - "all": 刷新全部
```

### 按情感/意图筛选客户

```bash
# 按情感标签筛选
curl "http://localhost:8000/api/v2/buyers/sentiment/Positive?limit=100"
curl "http://localhost:8000/api/v2/buyers/sentiment/Negative?limit=100"

# 按意图筛选
curl "http://localhost:8000/api/v2/buyers/intent/Pre-sale Inquiry?limit=100"
curl "http://localhost:8000/api/v2/buyers/intent/Complaint?limit=100"
```

---

## 测试指南

### API测试

```bash
# 测试AI分析（会触发多级降级）
curl "http://localhost:8000/api/v2/buyers/mylifemyrule?include_ai=true"

# 测试订单历史
curl "http://localhost:8000/api/v2/buyers/mylifemyrule/orders?limit=50"

# 测试聊天记录
curl "http://localhost:8000/api/v2/buyers/mylifemyrule/chats?limit=100"

# 清除AI缓存
curl -X POST "http://localhost:8000/api/v2/buyers/mylifemyrule/invalidate-cache"
```

### 控制台日志示例

```
[Orchestrator] 分析 弄箫居士
  - 聊天记录: 15条
  - VIP等级: V1

[L1-DeepSeek] 使用DeepSeek-R1分析 弄箫居士
✅ 分析完成 (耗时: 45.2秒)
   方法: DeepSeek-R1
   成本: ¥7.00

[Cache] Cached 弄箫居士 for 14 days
```

### 降级日志示例

```
[L1-DeepSeek] 使用DeepSeek-R1分析 mylifemyrule
[L1→L2] DeepSeek API余额不足(429)，降级到Zhipu GLM-4.7
[L2-Zhipu] 使用Zhipu GLM-4.7分析 mylifemyrule
✅ 分析完成 (耗时: 8.5秒)
   方法: Zhipu-GLM-4.7
   成本: ¥0.00
```

---

## 重要文档链接

### 核心文档

- [AI客户画像分析 v3.0](./docs/功能文档/AI客户画像分析.md) - AI功能详细说明
- [AI优化总结](./docs/plans/2026-02-24-ai-optimization-summary.md) - 降本增效与缓存策略
- [项目进度历史](./docs/项目记录/项目进度历史.md) - 开发历程
- [下一步计划](./docs/项目记录/下一步计划.md) - 未来规划

### 技术文档

- [数据模型设计](./docs/架构设计/数据模型设计.md) - 标签体系
- [目标买家功能总结](./docs/用户文档/目标买家功能总结.md) - 功能概述
- [Claude使用指南](./CLAUDE.md) - AI助手使用

---

## 常见问题

### Q1: AI分析返回错误或数据为0

**解决方案**:

```bash
# 检查API密钥配置
cat .env | grep -E "(DEEPSEEK|ZHIPU)"

# 检查AI客户端连接
python -c "from backend.ai import DeepSeekClient; print('DeepSeek连接正常')"
python -c "from backend.ai import ZhipuClient; print('Zhipu连接正常')"
```

### Q2: DeepSeek 429错误

**解决方案**: 系统会自动降级到Zhipu GLM-4.7，无需手动处理。如需检查降级状态，查看控制台日志。

### Q3: AI分析速度慢

**解决方案**:

- 检查缓存是否命中（查看日志中的 `cache_status: HIT`）
- 如缓存未命中，首次分析需要60-90秒
- 后续访问将使用缓存，响应时间<0.5秒

### Q4: 前端显示"No purchase history found"

**解决方案**:

- 确保后端服务正常运行
- 检查数据库连接
- 查看浏览器控制台错误

---

## 开发工作流

### 1. 开始新功能开发

```bash
# 1. 创建新分支
git checkout -b feature/your-feature-name

# 2. 开发功能
# 编写代码...

# 3. 测试
npm run test          # 前端测试
python tests/         # 后端测试

# 4. 提交代码
git add .
git commit -m "feat: description"

# 5. 推送到GitHub
git push origin feature/your-feature-name
```

### 2. AI功能开发注意事项

- 检查 `backend/ai/analyzer_orchestrator.py` 了解降级逻辑
- 新增分析字段时更新缓存表结构
- 测试三个降级层级是否正常工作
- 更新 `cache_strategy.py` 调整TTL策略

---

## 开发前检查清单

在开始开发前，确保：

- [ ] 后端服务正常运行（http://localhost:8000）
- [ ] 前端服务正常运行（http://localhost:3000）
- [ ] 数据库连接正常
- [ ] DeepSeek API密钥已配置
- [ ] Zhipu API密钥已配置（备选）
- [ ] `.env` 文件配置完整
- [ ] Git分支正确
- [ ] 已阅读相关文档
- [ ] 了解最近的重要修改

---

## 快速恢复上下文

1. **看这个文档** - 了解当前状态
2. **看提交历史** - `git log --oneline -10`
3. **看AI优化总结** - `docs/plans/2026-02-24-ai-optimization-summary.md`
4. **看项目进度历史** - `docs/项目记录/项目进度历史.md`
5. **启动服务测试** - 确保环境正常

---

**最后更新：** 2026-02-27
**当前分支：** feature/sql-field-names-update
**下次审查：** 根据开发进度
