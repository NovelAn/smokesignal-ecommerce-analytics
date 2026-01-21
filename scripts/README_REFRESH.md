# 手动刷新目标买家预计算表

## 📋 刷新方式对比

| 方式 | 速度 | 输出 | 推荐场景 |
|------|------|------|----------|
| **快速刷新** | ⚡ 最快 | 仅成功/失败 | 日常快速刷新 |
| **刷新+统计** | 📊 快速 | 关键指标 | 需要查看数据概览 |
| **Python脚本** | 🐌 较慢 | 详细报告 | 完整验证和调试 |
| **MySQL命令** | ⚡ 最快 | 无输出 | 极速刷新 |

---

## 🚀 推荐方式（Windows）

### 方式 1：快速刷新（最常用）

```cmd
scripts\refresh_quick.bat
```

**输出**：
```
[2026-01-20 17:30:00] 开始刷新目标买家预计算表...
[2026-01-20 17:37:04] ✓ 刷新成功！
```

**优点**：最快、最简单、清晰反馈

---

### 方式 2：刷新 + 统计信息

```cmd
scripts\refresh_with_stats.bat
```

**输出**：
```
========================================
[2026-01-20 17:30:00] 目标买家预计算表刷新
========================================

[1/2] 执行刷新...
[2/2] 获取统计信息...

┌─────────────────────────────────────┐
│        刷新完成 - 数据统计          │
└─────────────────────────────────────┘

📊 目标买家总数: 402
⏱️  最后更新: 2026-01-20 17:37:04
🔥 Smoker: 281
💎 VIC: 103
👑 BOTH: 18

========================================
✓ 刷新完成！
========================================
```

**优点**：快速 + 关键指标，适合日常使用

---

## 🐧 推荐方式（Linux/Mac）

### 方式 1：快速刷新

```bash
chmod +x scripts/refresh_quick.sh
./scripts/refresh_quick.sh
```

### 方式 2：刷新 + 统计信息

```bash
chmod +x scripts/refresh_with_stats.sh
./scripts/refresh_with_stats.sh
```

---

## ⚡ 极速刷新（命令行）

### Windows
```cmd
mysql -h rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com -u novelan -pAnna069832- dunhill -e "CALL refresh_target_buyers_precomputed();"
```

### Linux/Mac
```bash
mysql -h rm-uf68p191h7j2o40s34o.mysql.rds.aliyuncs.com -u novelan -pAnna069832- dunhill -e "CALL refresh_target_buyers_precomputed();"
```

**优点**：无需脚本，一条命令完成

---

## 🐍 Python 脚本（详细验证）

```bash
python scripts/refresh_target_buyers.py
```

**输出**：包含执行时间、详细统计、VIP分布、流失风险等

**适用场景**：
- 完整的数据验证
- 调试存储过程
- 查看所有指标详情

---

## 📊 验证刷新结果

### 快速验证（查看最后更新时间）
```sql
SELECT MAX(updated_at) as last_update FROM target_buyers_precomputed;
```

### 查看买家总数
```sql
SELECT COUNT(*) as total FROM target_buyers_precomputed;
```

### 查看类型分布
```sql
SELECT buyer_type, COUNT(*) as count
FROM target_buyers_precomputed
GROUP BY buyer_type;
```

---

## ⚙️ 性能对比

| 方式 | 预计耗时 | 说明 |
|------|---------|------|
| 快速刷新 | ~7分钟 | 仅执行存储过程 |
| 刷新+统计 | ~7分钟 | 执行 + 简单查询 |
| Python脚本 | ~7-8分钟 | 执行 + 详细查询 + 格式化 |
| MySQL命令 | ~7分钟 | 直接调用存储过程 |

*实际耗时取决于数据量和服务器性能*

---

## 🎯 推荐使用

### 日常使用（推荐）
```cmd
scripts\refresh_quick.bat
```
**最快、最简单**

### 需要查看数据
```cmd
scripts\refresh_with_stats.bat
```
**快速 + 关键指标**

### 调试和详细分析
```bash
python scripts/refresh_target_buyers.py
```
**完整验证和详细报告**

---

## 📝 注意事项

1. **自动刷新已配置**：每天上午 11:00 自动执行，通常无需手动刷新
2. **手动刷新场景**：
   - 紧急更新数据
   - 测试存储过程
   - 修改数据后立即生效
3. **刷新耗时**：约 7 分钟，期间不要中断
4. **并发安全**：存储过程设计为可重入，可安全多次执行

---

## 🔗 相关文件

- `scripts/refresh_quick.bat` - Windows 快速刷新
- `scripts/refresh_with_stats.bat` - Windows 刷新+统计
- `scripts/refresh_quick.sh` - Linux/Mac 快速刷新
- `scripts/refresh_with_stats.sh` - Linux/Mac 刷新+统计
- `scripts/refresh_target_buyers.py` - Python 详细验证

---

**文档版本**: 1.0
**最后更新**: 2026-01-20
