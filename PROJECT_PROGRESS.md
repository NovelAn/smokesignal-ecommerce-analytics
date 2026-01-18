# SmokeSignal Analytics - 项目开发进度

**最后更新：** 2026-01-16
**项目状态：** 后端开发阶段（性能优化中）

---

## ✅ 已完成的工作

### 1. 数据分析和模型设计
- ✅ 分析了MySQL数据库结构（`dunhill_t01_trade_line` 视图 + `chat_history` 表）
- ✅ 分析了订单数据字段（买家昵称、GMV、退款金额、品类等）
- ✅ 设计了完整的买家标签体系
- ✅ 创建了 `ANALYTICS_MODEL.md` 文档

### 2. 后端API服务开发
- ✅ 创建了完整的FastAPI后端项目结构
- ✅ 实现了数据库连接（复用chat-history-crawler的配置）
- ✅ 实现了所有核心数据分析模块：
  - `TagCalculator` - 标签计算逻辑
  - `BuyerAnalyzer` - 主分析引擎
  - `ZhipuClient` - 智谱AI集成
- ✅ 实现了8个API接口（买家列表、画像、订单、聊天、Dashboard等）
- ✅ 集成了智谱GLM-4.7 API

### 3. 标签计算实现
- ✅ VIP等级（Rolling 24个月，与线下CRM一致）
- ✅ 折扣敏感度（高/中/低）
- ✅ 流失风险（流失客户/流失预警）
- ✅ 购买频率、聊天活跃度
- ✅ 客户生命周期、品类偏好
- ✅ 高价值客户标签

### 4. 查询性能优化
- ✅ 添加了分页功能（默认100条）
- ✅ 添加了日期过滤
- ✅ 添加了搜索功能
- ✅ 添加了5分钟内存缓存
- ✅ 修复了SQL查询中的NULL值问题（`IFNULL(退款金额, 0)`）
- ✅ 优化了SQL查询（使用GROUP BY替代DISTINCT）

### 5. 配置和部署准备
- ✅ 配置了数据库连接（使用aliyun数据库）
- ✅ 创建了 `.env` 配置文件
- ✅ 创建了启动脚本 `start-backend.bat`
- ✅ 集成了智谱API key

---

## 🔄 当前进行中的工作

### 性能优化（最重要！）

**问题：**
- `dunhill_t01_trade_line` 是复杂视图（7个JOIN + UNION）
- 查询速度慢（几秒到几十秒）

**解决方案：**
创建了 `buyer_summary` 汇总表方案

**需要执行：**
1. 运行 `create_buyer_summary_table_optimized.sql` 创建汇总表
2. 在基础表上创建索引
3. 设置定时任务（每天凌晨2点自动更新）

**文件位置：**
- SQL脚本：`create_buyer_summary_table_optimized.sql`
- 实施指南：`PERFORMANCE_OPTIMIZATION_GUIDE.md`

**预期效果：**
- 查询速度提升 **100-1000倍**
- 从几秒降至几毫秒

---

## 📋 待办事项清单 (TODO)

### 立即需要完成（高优先级）

- [ ] **执行SQL优化脚本**
  - 在aliyun数据库中执行 `create_buyer_summary_table_optimized.sql`
  - 验证 `buyer_summary` 表创建成功
  - 检查数据导入是否正确

- [ ] **测试优化后的查询性能**
  - 重启后端服务
  - 测试 `/api/buyers` 接口速度
  - 确认响应时间 < 1秒

- [ ] **替换前端mock data**
  - 修改 `App.tsx` 中的API调用
  - 移除 `constants.ts` 中的mock数据
  - 实现真实API数据加载
  - 添加加载状态和错误处理

### 后续工作（中优先级）

- [ ] **前端功能增强**
  - 添加日期选择器UI
  - 添加搜索框
  - 实现分页加载
  - 优化用户体验

- [ ] **AI分析集成**
  - 测试智谱API调用
  - 实现买家画像分析
  - 实现情绪分析
  - 实现意图分析

- [ ] **部署方案设计**
  - 前后端打包配置
  - Docker容器化
  - 服务器部署方案
  - 域名和SSL证书配置

---

## ⚠️ 遇到的问题

### 问题1：数据库配置复用
**描述：** 不想重复写数据库配置，想使用chat-history-crawler的方法

**状态：** ✅ 已解决

**解决方案：**
- 复制了 `db_config_manager.py` 到backend项目
- 修改了 `config.py` 和 `connection.py` 使用DBConfigManager
- 从 `~/database_config.json` 读取配置

---

### 问题2：退款金额NULL导致计算错误
**描述：** 退款金额为NULL时，netsales计算不出来

**状态：** ✅ 已解决

**解决方案：**
- 所有SQL查询中使用 `IFNULL(退款金额, 0)` 处理NULL值
- 修改了5个SQL查询方法

---

### 问题3：PyMySQL cursorclass错误
**描述：** `'str' object is not callable`

**状态：** ✅ 已解决

**解决方案：**
- 修改 `db_config_manager.py`
- 使用 `pymysql.cursors.DictCursor` 类对象而不是字符串

---

### 问题4：查询速度慢（当前主要问题）
**描述：**
- `dunhill_t01_trade_line` 是复杂视图
- 包含7个LEFT JOIN + UNION
- 每次查询都重新计算
- 速度：几秒到几十秒

**状态：** 🔄 解决方案已准备，待执行

**解决方案：**
- 创建 `buyer_summary` 汇总表
- 在基础表上创建索引
- 设置定时自动刷新（每天凌晨2点）
- 后端已修改为使用汇总表查询

**预期效果：** 速度提升100-1000倍

---

## 🔧 需要解决的技术问题

### 问题1：视图索引
**描述：** `dunhill_t01_trade_line` 是视图，不能创建索引

**影响：** 查询性能差

**解决方案：**
- ✅ 创建基础表索引（`dunhill_bi订单源`、`dunhill_dtc订单源_hive`）
- ✅ 创建汇总表 `buyer_summary`

**需要执行：**
```sql
-- 在aliyun数据库中执行
CREATE INDEX idx_bi_buyer_nick ON dunhill_bi订单源(买家昵称);
CREATE INDEX idx_dtc_buyer_nick ON dunhill_dtc订单源_hive(买家昵称);
-- 以及其他索引（见SQL脚本）
```

---

### 问题2：数据更新频率
**描述：** 汇总表需要定期更新

**解决方案：**
- ✅ 创建了存储过程 `refresh_buyer_summary()`
- ✅ 创建了定时任务（每天凌晨2点）
- ✅ 支持手动刷新

**需要确认：**
- 数据更新频率（每天凌晨2点）是否可接受？
- 手动刷新流程是否清晰？

---

### 问题3：前端集成
**描述：** 前端App.tsx是58KB的单文件，需要集成API

**待解决：**
- [ ] 修改API调用地址（改为 `http://localhost:8000/api/...`）
- [ ] 实现数据获取逻辑
- [ ] 添加loading状态
- [ ] 添加错误处理
- [ ] 实现分页加载
- [ ] 实现日期过滤
- [ ] 实现搜索功能

---

## 📁 项目文件结构

```
smokesignal-analytics/
├── App.tsx                    # 前端主文件（58KB，待修改）
├── types.ts                   # TypeScript类型定义
├── constants.ts               # Mock数据（待替换为API）
├── index.html
├── vite.config.ts
├── package.json
├── tsconfig.json
│
├── ANALYTICS_MODEL.md         # 数据分析模型设计文档
├── CLAUDE.md                  # Claude Code使用指南
├── BACKEND_FIXES.md           # 后端修复记录
├── PERFORMANCE_OPTIMIZATION_GUIDE.md  # 性能优化指南
├── PROJECT_PROGRESS.md        # 本文件
│
├── create_buyer_summary_table_optimized.sql  # 性能优化SQL脚本
├── dunhill_t01_trade_line.sql # 视图定义
│
└── backend/                   # 后端服务（已开发完成）
    ├── main.py                # FastAPI入口
    ├── config.py              # 配置管理
    ├── requirements.txt       # Python依赖
    ├── .env                   # 环境变量
    ├── .env.example
    ├── start-backend.bat      # 启动脚本
    │
    ├── analytics/             # 数据分析模块
    │   ├── __init__.py
    │   ├── tag_calculator.py  # 标签计算
    │   └── buyer_analyzer.py  # 买家分析
    │
    ├── database/              # 数据库模块
    │   ├── __init__.py
    │   ├── connection.py      # 数据库连接
    │   ├── queries.py         # SQL查询（已优化）
    │   ├── cache.py           # 内存缓存
    │   └── db_config_manager.py  # 配置管理
    │
    ├── ai/                    # AI模块
    │   ├── __init__.py
    │   └── zhipu_client.py    # 智谱AI集成
    │
    └── api/                   # API路由
        ├── __init__.py
        └── routes.py          # API端点
```

---

## 🗄️ 数据库信息

### 数据库配置
- **配置文件：** `~/database_config.json`（与chat-history-crawler共享）
- **使用数据库：** aliyun（第三个配置）
- **表结构：**
  - `dunhill_t01_trade_line` - 订单视图（复杂，7个JOIN）
  - `chat_history` - 聊天记录表
  - `buyer_summary` - 买家汇总表（待创建）

### 关键字段
- `买家昵称` - 关联字段
- `订单号` / `子订单号` - 订单标识
- `最后付款时间` - 订单时间
- `成交总金额` - GMV
- `退款金额` - 退款（可能为NULL）
- `FP_MD` - FP=正价品，MD=折扣品
- `category` - 商品品类
- `client_monthly_tag` - 新老客类型

---

## 🔌 API接口清单

### 已实现的接口

| 方法 | 路径 | 描述 | 状态 |
|------|------|------|------|
| GET | `/api/buyers` | 获取买家列表（支持分页、搜索、日期过滤） | ✅ 已优化 |
| GET | `/api/buyers/{user_nick}` | 获取买家完整画像 | ✅ 完成 |
| GET | `/api/buyers/{user_nick}/orders` | 获取订单历史 | ✅ 完成 |
| GET | `/api/buyers/{user_nick}/chats` | 获取聊天记录 | ✅ 完成 |
| POST | `/api/buyers/{user_nick}/ai-analysis` | 触发AI分析 | ✅ 完成 |
| GET | `/api/dashboard/metrics` | Dashboard指标 | ✅ 完成 |
| GET | `/api/dashboard/daily-stats` | 每日统计 | ✅ 完成 |
| GET | `/api/dashboard/actionable-customers` | 需关注客户 | ✅ 完成 |

### API查询参数示例

```bash
# 默认查询（100条）
/api/buyers

# 分页
/api/buyers?limit=50&offset=100

# 搜索
/api/buyers?search=崔

# 日期过滤
/api/buyers?start_date=2024-01-01&end_date=2024-12-31

# 组合查询
/api/buyers?search=华&start_date=2024-01-01&limit=20
```

---

## 📊 VIP等级标准（与线下CRM一致）

**计算基础：** Rolling 24个月 netsales

| 等级 | Netsales范围 |
|------|--------------|
| Non-VIP | < 30,000元 |
| V0 | 30,000 - 49,999元 |
| V1 | 50,000 - 149,999元 |
| V2 | 150,000 - 449,999元 |
| V3 | ≥ 450,000元 |

**计算公式：**
```sql
SELECT SUM(成交总金额 - IFNULL(退款金额, 0)) as rolling_netsales
FROM dunhill_t01_trade_line
WHERE 最后付款时间 >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
```

---

## 🤖 智谱AI配置

**API Key：** `0952801ba29f4365b9298fc0fc3b9e80.OlryWE4QUP8Surq4`
**模型：** `glm-4-plus`
**用途：**
- 买家画像分析（summary）
- 关键兴趣点提取（key_interests）
- 痛点分析（pain_points）
- 推荐行动（recommended_action）
- 情绪分析
- 意图分布分析

---

## 🚀 下次继续的工作

### 第一步：完成性能优化（最高优先级）
1. 在aliyun数据库执行 `create_buyer_summary_table_optimized.sql`
2. 验证 `buyer_summary` 表创建成功
3. 重启后端服务
4. 测试API查询速度（目标：< 1秒）

### 第二步：替换前端mock data
1. 修改 `App.tsx` 中的数据获取逻辑
2. 连接真实API
3. 添加加载状态和错误处理
4. 测试前端功能

### 第三步：前端功能增强
1. 添加日期选择器
2. 添加搜索功能
3. 实现分页加载

### 第四步：部署准备
1. 打包配置
2. Docker化
3. 服务器部署

---

## 📞 重要提示

### 数据库操作提醒
⚠️ **执行SQL脚本前请确认：**
- 在aliyun数据库执行
- 确保有足够的权限（CREATE TABLE, CREATE INDEX, CREATE EVENT）
- 首次执行需要5-15分钟，请耐心等待
- 建议在非高峰期执行

### 后端服务
- 当前运行在：`http://localhost:8000`
- 启动方式：`python -m backend.main` 或双击 `start-backend.bat`
- API文档：`http://localhost:8000/docs`

### 配置文件
- 数据库配置：`~/database_config.json`
- 后端配置：`backend/.env`

---

## 🎯 项目目标

### 短期目标
- ✅ 完成后端API开发
- 🔄 完成性能优化
- ⏳ 完成前端API集成
- ⏳ 实现核心分析功能

### 中期目标
- 实现AI智能分析
- 实现数据可视化
- 完成用户测试

### 长期目标
- 部署到生产环境
- 分享给团队使用
- 持续优化和迭代

---

## 📝 备注

### 设计决策
1. **使用Python FastAPI** - 与chat-history-crawler技术栈一致
2. **使用汇总表方案** - 性能优化的最佳方案
3. **数据更新频率** - 每天凌晨2点（可接受）
4. **VIP等级标准** - 与线下CRM完全一致

### 技术债务
1. `App.tsx` 文件过大（58KB），需要拆分
2. 前端缺少路由（使用state管理）
3. 没有测试覆盖
4. 缺少错误边界

### 已知限制
1. 汇总表有延迟（每天更新）
2. 基础表索引可能影响写入性能（轻微）
3. AI分析需要几秒钟（异步处理）

---

**祝好！下次继续！👋**
