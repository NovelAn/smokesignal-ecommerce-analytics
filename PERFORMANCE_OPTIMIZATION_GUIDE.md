# 性能优化实施指南

## 📊 优化方案总结

### 问题
- `dunhill_t01_trade_line` 是复杂视图，包含7个JOIN和UNION
- 每次查询都重新计算，速度慢

### 解决方案
1. ✅ 在基础表上创建索引
2. ✅ 创建 `buyer_summary` 汇总表
3. ✅ 定时自动刷新（每天凌晨2点）
4. ✅ 后端改用汇总表查询

---

## 🚀 实施步骤

### Step 1: 执行SQL脚本（约需5-10分钟）

在MySQL（aliyun数据库）中执行：

```bash
# 方式1: 命令行执行
mysql -u your_user -p aliyun < D:\Work\ai\projects\smokesignal-analytics\create_buyer_summary_table_optimized.sql

# 方式2: MySQL客户端
# 打开MySQL客户端，复制粘贴整个SQL文件内容执行
```

**SQL会自动完成以下操作：**
1. 在基础表上创建索引（加快视图查询）
2. 创建 `buyer_summary` 表
3. 从视图导入初始数据
4. 创建存储过程 `refresh_buyer_summary()`
5. 创建定时任务（每天凌晨2点）

**预计耗时：**
- 首次导入数据：5-15分钟（取决于数据量）

---

### Step 2: 验证安装

执行以下SQL验证：

```sql
-- 1. 检查表是否创建成功
SHOW TABLES LIKE 'buyer_summary';

-- 2. 查看买家数量
SELECT COUNT(*) as total_buyers FROM buyer_summary;

-- 3. 查看样例数据
SELECT * FROM buyer_summary LIMIT 10;

-- 4. 检查定时任务
SHOW EVENTS WHERE EVENT_NAME = 'event_refresh_buyer_summary';

-- 5. 检查存储过程
SHOW PROCEDURE STATUS WHERE Name = 'refresh_buyer_summary';
```

---

### Step 3: 重启后端服务

后端代码已修改，使用新的 `buyer_summary` 表。

1. 停止当前后端服务（Ctrl+C）
2. 重新启动：
```bash
python -m backend.main
```

---

### Step 4: 测试性能

在浏览器测试API：

```
http://localhost:8000/api/buyers
```

**预期结果：**
- ✅ 第一次查询：毫秒级响应（< 1秒）
- ✅ 第二次查询：飞快（有缓存）
- ✅ 返回格式正确

---

## 📈 性能对比

### 优化前
```
SELECT DISTINCT 买家昵称 FROM dunhill_t01_trade_line
```
- 每次查询都要计算7个JOIN + UNION
- 耗时：几秒到几十秒

### 优化后
```
SELECT buyer_nick FROM buyer_summary ORDER BY last_order_date DESC
```
- 直接从汇总表读取（有索引）
- 耗时：几毫秒

**速度提升：100-1000倍** ⚡

---

## 🔄 数据更新

### 自动更新（推荐）
- 每天凌晨2点自动执行 `CALL refresh_buyer_summary()`
- 无需人工干预

### 手动更新
如需立即更新数据：

```sql
CALL refresh_buyer_summary();
```

执行后会显示：
- 更新了多少条记录
- 耗时多少秒
- 当前买家总数

---

## 🛠️ 维护命令

### 查看更新时间
```sql
SELECT MAX(updated_at) as last_updated FROM buyer_summary;
```

### 查看事件调度器状态
```sql
SHOW VARIABLES LIKE 'event_scheduler';
```

### 启用/禁用事件调度器
```sql
-- 启用
SET GLOBAL event_scheduler = ON;

-- 禁用
SET GLOBAL event_scheduler = OFF;
```

### 手动触发定时任务
```sql
-- 立即执行一次
CALL refresh_buyer_summary();
```

---

## ⚠️ 注意事项

1. **数据延迟**
   - 汇总表每天凌晨2点更新
   - 今天最多能看到昨天的数据
   - 如需实时数据，手动执行 `CALL refresh_buyer_summary();`

2. **首次导入**
   - 首次执行SQL可能需要5-15分钟
   - 请耐心等待，不要中断

3. **存储空间**
   - `buyer_summary` 表很小（约几MB）
   - 影响可忽略

4. **索引维护**
   - 基础表索引会轻微降低INSERT/UPDATE速度
   - 但查询速度大幅提升，值得

---

## 🆘 故障排查

### 问题1: 表创建失败
```
Error: Table 'buyer_summary' already exists
```
**解决：** 删除旧表重建
```sql
DROP TABLE IF EXISTS buyer_summary;
```
然后重新执行SQL脚本。

### 问题2: 事件调度器不工作
```
Error: Event scheduler is disabled
```
**解决：** 启用事件调度器
```sql
SET GLOBAL event_scheduler = ON;
```

### 问题3: 存储过程执行慢
**原因：** 基础表数据量大，视图计算复杂
**解决：**
- 确保基础表索引已创建
- 考虑在非高峰期执行

---

## 📞 需要帮助？

如果遇到问题，请提供：
1. 错误信息
2. 执行的SQL语句
3. 数据表大小（SELECT COUNT(*) FROM dunhill_t01_trade_line）

---

## ✅ 完成检查清单

- [ ] SQL脚本执行成功
- [ ] `buyer_summary` 表有数据
- [ ] 定时任务已创建
- [ ] 后端服务已重启
- [ ] API查询速度提升
- [ ] 手动刷新测试成功

全部完成后，我们就可以继续下一步：**替换前端mock data**！
