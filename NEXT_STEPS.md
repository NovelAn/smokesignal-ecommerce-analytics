# 下次继续 - 快速启动指南

**📍 当前进度：** 性能优化阶段（待执行SQL脚本）

---

## 🚀 明天第一步（最重要）

### 执行SQL优化脚本

```bash
# 1. 打开MySQL客户端，连接到aliyun数据库
mysql -u your_user -p aliyun

# 2. 执行优化脚本
source D:\Work\ai\projects\smokesignal-analytics\create_buyer_summary_table_optimized.sql

# 或者使用命令行
mysql -u your_user -p aliyun < D:\Work\ai\projects\smokesignal-analytics\create_buyer_summary_table_optimized.sql
```

**预计耗时：** 5-15分钟

---

## ✅ 验证成功（执行SQL后）

```sql
-- 检查表是否创建
SHOW TABLES LIKE 'buyer_summary';

-- 查看数据量
SELECT COUNT(*) FROM buyer_summary;

-- 查看样例
SELECT * FROM buyer_summary LIMIT 10;
```

---

## 🔄 重启后端

```bash
# 1. 停止当前服务（Ctrl+C）

# 2. 重新启动
cd D:\Work\ai\projects\smokesignal-analytics
python -m backend.main
```

---

## 🧪 测试API

打开浏览器访问：
```
http://localhost:8000/api/buyers
```

**预期：** 毫秒级响应（< 1秒）⚡

---

## 📋 后续任务

### 短期（本周）
- [ ] 完成性能优化验证
- [ ] 替换前端mock data
- [ ] 实现前端API集成
- [ ] 添加loading状态

### 中期（下周）
- [ ] 添加日期选择器UI
- [ ] 添加搜索功能
- [ ] 实现分页加载
- [ ] 测试AI分析功能

### 长期
- [ ] 代码重构（拆分App.tsx）
- [ ] 添加测试
- [ ] 部署到生产环境

---

## 📁 重要文件

| 文件 | 用途 |
|------|------|
| `PROJECT_PROGRESS.md` | 完整项目进度文档 |
| `PERFORMANCE_OPTIMIZATION_GUIDE.md` | 性能优化指南 |
| `create_buyer_summary_table_optimized.sql` | SQL优化脚本 |
| `backend/.env` | 后端配置（使用aliyun数据库） |
| `start-backend.bat` | 启动脚本 |

---

## 🔧 常用命令

```bash
# 启动后端
python -m backend.main

# 启动前端
npm run dev

# 查看API文档
# 浏览器打开: http://localhost:8000/docs

# 手动刷新汇总表（MySQL中执行）
CALL refresh_buyer_summary();
```

---

## 💡 关键信息

- **数据库：** aliyun（第3个配置）
- **后端地址：** http://localhost:8000
- **前端地址：** http://localhost:3000
- **配置文件：** ~/database_config.json

---

**有问题？查看 `PROJECT_PROGRESS.md` 获取完整信息！**
