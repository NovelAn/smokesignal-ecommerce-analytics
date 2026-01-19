# Backend Fixes - 修复总结

## ✅ 已完成的修复

### 1. 数据库配置复用 chat-history-crawler

**修改内容：**
- 复制 `db_config_manager.py` 到 `backend/database/`
- 修改 `config.py`，移除数据库配置字段
- 修改 `database/connection.py`，使用 `DBConfigManager` 从 `~/database_config.json` 读取配置
- 更新 `.env` 和 `.env.example`，移除数据库配置相关字段

**好处：**
- ✅ 统一配置管理，只需维护一个配置文件
- ✅ 与 chat-history-crawler 项目共享配置
- ✅ 减少配置重复，降低出错风险

**配置文件位置：**
```
~/database_config.json
```

---

### 2. SQL查询中的退款金额NULL处理

**问题：**
- 退款金额字段在数据库中可能为NULL（表示未退款）
- 直接计算 `成交总金额 - 退款金额` 时，如果退款金额为NULL，结果为NULL
- 导致无法正确计算 netsales

**修复方案：**
所有涉及退款金额计算的SQL语句都使用 `IFNULL(退款金额, 0)` 处理

**修改的查询：**
1. `get_buyer_basic_metrics` - 基础买家指标
2. `get_buyer_rolling_metrics` - Rolling 24个月指标
3. `get_buyer_l6m_metrics` - 近6个月指标
4. `get_buyer_category_preference` - 品类偏好
5. `get_buyer_order_history` - 订单历史

**修改示例：**
```sql
-- 修改前
SUM(成交总金额 - 退款金额) as historical_ltv

-- 修改后
SUM(成交总金额 - IFNULL(退款金额, 0)) as historical_ltv
```

---

## 📁 修改的文件列表

1. ✅ `backend/database/db_config_manager.py` - 新增
2. ✅ `backend/config.py` - 移除数据库配置
3. ✅ `backend/database/connection.py` - 使用DBConfigManager
4. ✅ `backend/database/queries.py` - 添加IFNULL处理
5. ✅ `backend/.env` - 移除数据库配置
6. ✅ `backend/.env.example` - 更新示例
7. ✅ `backend/README.md` - 更新文档

---

## 🧪 测试建议

### 1. 测试数据库连接

```bash
cd backend
python -c "from backend.database import Database; db = Database(); print('✅ Database connected successfully')"
```

### 2. 测试SQL查询

```bash
python -c "
from backend.database import Database, BuyerQueries
db = Database()
results = db.execute_query(BuyerQueries.get_buyer_basic_metrics())
print(f'✅ Found {len(results)} buyers')
if results:
    print(f'Sample buyer LTV: {results[0][\"historical_ltv\"]}')
"
```

### 3. 测试后端API

```bash
# 启动服务
python -m backend.main

# 测试API
curl http://localhost:8000/
curl http://localhost:8000/api/buyers
```

---

## 📝 下一步

后端修复已完成，可以：

1. ✅ 安装依赖并启动后端服务测试
2. ⏭️ 替换前端mock data为真实API调用
3. ⏭️ 设计线上部署方案

---

## ⚠️ 重要提醒

1. **确保配置文件存在**: `~/database_config.json` 必须存在且格式正确
2. **数据库表名**: 确认订单表名为 `dunhill_t01_trade_line`，聊天表名为 `chat_history`
3. **字段名**: 确认所有字段名与SQL查询中一致
4. **智谱API额度**: 确认API key有足够额度
