-- 检查数据库 DDL 操作历史
-- 注意：需要访问 mysql.general_log 或 binlog

-- 1. 检查是否启用了 general log
SHOW VARIABLES LIKE 'general_log%';

-- 2. 如果启用了，查找最近对视图的 DDL 操作
-- (需要查询 general_log 表，通常很大)
-- SELECT * FROM mysql.general_log
-- WHERE argument LIKE '%dunhill_t01_trade_line%'
--   AND command_type = 'Query'
-- ORDER BY event_time DESC
-- LIMIT 20;

-- 3. 检查 binlog 是否启用
SHOW VARIABLES LIKE 'log_bin%';

-- 4. 查看最近修改视图的操作
-- 需要使用 mysqlbinlog 工具分析 binlog 文件

-- 5. 检查其他视图是否也有问题
SELECT TABLE_NAME, CREATE_TIME
FROM information_schema.VIEWS
WHERE TABLE_SCHEMA = 'dunhill'
ORDER BY CREATE_TIME DESC;
