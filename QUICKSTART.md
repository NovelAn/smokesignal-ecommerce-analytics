---
category: 开发指南
title: 快速启动指南
tags: ['快速开始', '上下文恢复', '开发流程']
description: 快速恢复项目开发上下文和启动开发环境
priority: high
last_updated: 2025-01-20
---

# 🚀 SmokeSignal Analytics - 快速启动指南

**最后更新：** 2025-01-20
**当前版本：** v2.1
**当前分支：** `feature/target-buyers-precomputation-optimization`

---

## 📍 当前项目状态

### ✅ 已完成功能（v2.0 + v2.1）

1. **目标买家预计算系统**
   - 40-120x性能提升
   - 391个目标买家识别
   - 每日11:00自动刷新

2. **AI客户画像分析（v2.1新增）**
   - ✅ 数据准确性修复（字段名映射）
   - ✅ 洞察质量提升（深度行为分析）
   - ✅ 完整数据流（API→前端展示）
   - ✅ 订单历史查看
   - ✅ 聊天记录查看

3. **前端三大模块**
   - Dashboard Overview - 实时指标和可操作客户列表
   - Chat & CRM - 360°客户画像、AI分析、订单历史、聊天记录
   - Configuration - 管道状态和配置

### 🎯 技术栈

- **前端**: React 19.2.3 + TypeScript + Vite 6.2.0 + Recharts 3.6.0
- **后端**: FastAPI + Python
- **AI**: Zhipu GLM-4
- **数据库**: MySQL (阿里云RDS)
- **测试**: Playwright MCP (端到端测试)

---

## ⚡ 快速启动

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

## 🔧 开发环境配置

### 必需的环境变量

创建 `.env` 文件：

```bash
# 数据库配置
DB_CONFIG_FILE=~/database_config.json
DB_NAME_TO_USE=aliyunDB

# 智谱AI配置（必需，用于AI分析功能）
ZHIPU_API_KEY=your_api_key_here
ZHIPU_MODEL=glm-4-flash
```

### 获取智谱AI API密钥

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册账号并登录
3. 进入API密钥管理页面
4. 创建新的API密钥
5. 添加到 `.env` 文件

---

## 📂 项目结构速览

```
smokesignal-ecommerce-analytics/
├── backend/                      # Python后端
│   ├── ai/                      # AI客户端
│   │   └── zhipu_client.py      # 智谱AI封装（v2.1已优化）
│   ├── analytics/               # 数据分析
│   │   └── target_buyer_analyzer.py  # 目标买家分析器
│   ├── api/                     # API路由
│   │   └── target_routes.py     # v2 API路由（v2.1已优化）
│   ├── database/                # 数据库层
│   │   ├── sql/                 # SQL查询文件
│   │   └── target_buyer_queries.py
│   └── main.py                  # FastAPI应用入口
│
├── src/                         # React前端
│   ├── api/                     # API客户端封装
│   ├── components/              # React组件
│   ├── hooks/                   # 自定义Hooks
│   └── App.tsx                  # 主应用（v2.1已优化）
│
├── docs/                        # 文档
│   ├── 功能文档/                # 功能详细说明
│   │   └── AI客户画像分析.md    # AI功能文档（v2.1新增）
│   ├── 项目记录/                # 项目进度
│   │   ├── 项目进度历史.md      # 开发历程
│   │   └── 下一步计划.md        # 未来规划
│   └── 架构设计/                # 架构文档
│
├── scripts/                     # 工具脚本
│   └── start-backend.bat        # 后端启动脚本（Windows）
│
└── tests/                       # 测试文件
```

---

## 🔍 最近的重要修改（v2.1）

### 1. AI分析功能完善

**文件**: `backend/ai/zhipu_client.py`

- **修复**: 字段名映射 `historical_net_sales` vs `historical_ltv`
- **重写**: AI提示词，从简单重复到深度洞察
- **结果**: AI提供行为分析和个性化建议

**文件**: `backend/api/target_routes.py`

- **修复**: order_summary字段映射
- **增强**: 包含L6M占比、平均客单价、退款率等指标

### 2. 前端数据流修复

**文件**: `src/App.tsx`

- **添加**: 并行API调用获取orders和chats
- **实现**: 产品级→订单级数据转换
- **修复**: groupedMessages数据源问题

---

## 🧪 测试指南

### 端到端测试（Playwright MCP）

```bash
# 启动浏览器测试
# 已配置Playwright MCP，可直接使用MCP工具进行测试

# 测试场景：
# 1. 访问 http://localhost:3000
# 2. 点击"Chat & CRM"标签
# 3. 搜索客户"mylifemyrule"
# 4. 点击"AI分析"开关
# 5. 验证AI分析结果
# 6. 切换到"Purchase History"标签
# 7. 切换到"Communication"标签
```

### API测试

```bash
# 测试AI分析
curl "http://localhost:8000/api/v2/buyers/mylifemyrule?include_ai=true"

# 测试订单历史
curl "http://localhost:8000/api/v2/buyers/mylifemyrule/orders?limit=50"

# 测试聊天记录
curl "http://localhost:8000/api/v2/buyers/mylifemyrule/chats?limit=100"
```

---

## 📚 重要文档链接

### 核心文档
- [AI客户画像分析](./docs/功能文档/AI客户画像分析.md) - AI功能详细说明 ⭐
- [项目进度历史](./docs/项目记录/项目进度历史.md) - 开发历程
- [下一步计划](./docs/项目记录/下一步计划.md) - 未来规划

### 技术文档
- [数据模型设计](./docs/架构设计/数据模型设计.md) - 标签体系
- [目标买家功能总结](./docs/用户文档/目标买家功能总结.md) - 功能概述
- [Claude使用指南](./CLAUDE.md) - AI助手使用

---

## 🚨 常见问题

### Q1: AI分析返回错误或数据为0

**解决方案**:
```bash
# 检查API密钥配置
cat .env | grep ZHIPU_API_KEY

# 测试智谱AI连接
python -c "from backend.ai import ZhipuClient; client = ZhipuClient(); print('API连接正常')"
```

### Q2: 前端显示"No purchase history found"

**解决方案**:
- 确保后端服务正常运行
- 检查数据库连接
- 查看浏览器控制台错误

### Q3: Communication模块无聊天记录

**解决方案**:
- 检查`src/App.tsx`中`groupedMessages`的数据源
- 验证API `/api/v2/buyers/{user_nick}/chats`返回数据

---

## 🎯 下一步开发重点

### 短期（1-2周）

1. **AI分析增强** ⭐
   - 批量AI分析功能
   - AI对比分析（不同客户群体）
   - AI报告生成

2. **前端优化**
   - 添加加载状态指示器
   - 错误处理优化
   - 响应式布局改进

3. **数据增强**
   - RFM模型评分
   - 客户生命周期阶段识别
   - 购买频率分析

### 中期（1个月）

1. **监控告警系统**
   - API性能监控
   - 数据刷新失败告警
   - 异常数据自动检测

2. **安全加固**
   - API身份认证（JWT）
   - 请求频率限制
   - HTTPS强制跳转

3. **数据导出**
   - Excel/CSV导出
   - 自定义报表生成

---

## 💻 开发工作流

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

### 2. 使用Claude Code开发

```markdown
启动Claude Code时，告诉Claude：
- 当前项目状态（参考本文档）
- 需要开发的功能
- 相关的技术约束

Claude会：
1. 分析代码结构
2. 提出实现方案
3. 编写代码
4. 更新文档
```

---

## 📞 获取帮助

- **GitHub Issues**: [提交问题](https://github.com/NovelAn/smokesignal-ecommerce-analytics/issues)
- **文档中心**: [docs/README.md](./docs/README.md)
- **项目记录**: [docs/项目记录/](./docs/项目记录/)

---

## ✅ 开发前检查清单

在开始开发前，确保：

- [ ] 后端服务正常运行（http://localhost:8000）
- [ ] 前端服务正常运行（http://localhost:3000）
- [ ] 数据库连接正常
- [ ] 智谱AI API密钥已配置
- [ ] `.env` 文件配置完整
- [ ] Git分支正确（`feature/target-buyers-precomputation-optimization`）
- [ ] 已阅读相关文档
- [ ] 了解最近的重要修改

---

**快速恢复上下文的关键提示**:

1. **看这个文档** - 了解当前状态
2. **看提交历史** - `git log --oneline -10`
3. **看项目进度历史** - `docs/项目记录/项目进度历史.md`
4. **看下一步计划** - `docs/项目记录/下一步计划.md`
5. **启动服务测试** - 确保环境正常

---

**最后更新：** 2025-01-20
**当前分支：** feature/target-buyers-precomputation-optimization
**下次审查：** 根据开发进度
