# SmokeSignal Analytics - API Integration Status

## 已完成的工作

### 1. 后端 API 搭建 ✅
- FastAPI 后端已启动，运行在 `http://localhost:8000/api`
- 8个 API 端点已实现：
  - `GET /buyers` - 买家列表（支持分页、搜索、日期过滤）
  - `GET /buyers/{user_nick}` - 买家完整画像
  - `GET /buyers/{user_nick}/orders` - 买家订单历史
  - `GET /buyers/{user_nick}/chats` - 买家聊天记录
  - `GET /dashboard/metrics` - Dashboard 总览指标
  - `GET /dashboard/daily-stats` - 每日统计数据
  - `GET /dashboard/actionable-customers` - 需关注客户列表
  - `POST /buyers/{user_nick}/ai-analysis` - AI 买家分析

### 2. 数据库优化 ✅
- 创建了 `buyer_summary` 汇总表（29,825 位买家）
- 修复了所有视图问题（`dunhill_t01_trade_line` 等）
- 更新了存储过程 `refresh_buyer_summary()` 包含退款数据
- 查询性能从数秒优化到 <1 秒（针对买家列表查询）

### 3. 前端 API 集成 ✅
- 创建了 `api.ts` API 客户端类
- 创建了 `AppDemo.tsx` 演示页面，包含：
  - Dashboard 概览（4个关键指标卡片）
  - VIP 客户分布可视化
  - 需关注客户列表（84 位）
  - 买家列表搜索（29,825 位买家）
- 前端开发服务器运行在 `http://localhost:3000`

### 4. API 类型定义 ✅
更新了 TypeScript 接口以匹配后端响应：
```typescript
export interface DashboardMetrics {
  total_buyers: number;
  total_ltv: number;
  total_orders: number;
  total_chats: number;
  avg_ltv: number;
  vip_distribution: { ... };
}
```

## 当前问题

### API 响应超时 ⚠️
**问题：** 后端 API 端点响应时间过长（>30秒），导致前端请求超时

**原因分析：**
1. `get_dashboard_metrics()` 端点需要执行复杂聚合查询
2. `get_buyer_basic_metrics()` 查询扫描 `dunhill_t01_trade_line` 视图（58,123 条记录）
3. `get_chat_summary_metrics()` 需要聚合聊天数据
4. VIP 级别计算需要遍历所有买家记录

**受影响的端点：**
- `/api/dashboard/metrics` - Dashboard 指标（超时）
- `/api/dashboard/actionable-customers` - 需关注客户（超时）

**未受影响的端点：**
- `/api/buyers` - 买家列表（使用 `buyer_summary` 表，速度快）
- `/api/buyers/{user_nick}` - 单个买家画像（速度快）

## 性能优化建议

### 短期方案
1. **创建额外的汇总表**
   - `dashboard_metrics` 表：预计算 Dashboard 指标
   - `actionable_customers` 物化视图：预计算需关注客户

2. **添加数据库索引**
   - 在 `dunhill_t01_trade_line` 的 `买家昵称`、`最后付款时间` 字段
   - 在 `chat_history` 的 `user_nick`、`msg_time` 字段

3. **API 响应缓存**
   - 使用 Redis 缓存 Dashboard 指标（5分钟过期）
   - 缓存需关注客户列表（10分钟过期）

### 长期方案
1. **数据库分库分表**
   - 按年份分割订单数据
   - 按月份分割聊天数据

2. **读写分离**
   - 查询操作使用只读副本
   - 写入操作使用主数据库

3. **异步任务队列**
   - 使用 Celery 执行耗时计算
   - 前端轮询任务状态获取结果

## 测试命令

### 测试后端 API
```bash
# 快速查询（<1秒）
curl http://localhost:8000/api/buyers?limit=5

# 慢速查询（>30秒，超时）
curl http://localhost:8000/api/dashboard/metrics
curl http://localhost:8000/api/dashboard/actionable-customers
```

### 访问前端
- 打开浏览器访问: http://localhost:3000
- 点击 "Dashboard" 查看概览（会超时）
- 点击 "买家列表" 查看买家列表（正常）

## 下一步

需要决定如何处理性能问题：
1. **创建 Dashboard 汇总表**（推荐，1-2小时工作量）
2. **添加 Redis 缓存**（需要安装 Redis）
3. **接受当前性能**（使用加载指示器和超时处理）

请告诉我您希望如何继续。

---

**相关文件：**
- `api.ts` - 前端 API 客户端
- `AppDemo.tsx` - API 集成演示页面
- `backend/api/routes.py` - FastAPI 路由定义
- `backend/database/queries.py` - SQL 查询定义
- `test_api_integration.py` - API 测试脚本
- `restart_backend.py` - 后端服务器重启脚本
