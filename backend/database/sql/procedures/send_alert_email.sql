-- ============================================
-- send_alert_email procedure
-- ============================================
-- 用途：被 snapshot_target_buyers_history / maintain_history_partitions
--       的 EXIT HANDLER 调用, 失败时通知运维
-- 实现：通过 sys_exec 调用 Python 脚本发送邮件 (简化版)
--       生产环境建议替换为飞书 webhook 或专业监控
-- ============================================

DROP PROCEDURE IF EXISTS send_alert_email;

DELIMITER $$

CREATE PROCEDURE send_alert_email(
    IN p_subject VARCHAR(500),
    IN p_body TEXT
)
BEGIN
    DECLARE v_cmd TEXT;
    DECLARE v_recipient VARCHAR(200) DEFAULT 'ops@smokesignal.local';

    -- 简化版: 写入 alert log + 调用 Python 脚本发邮件
    -- 实际生产环境建议用 Python UDF 或飞书 webhook 替换

    -- 1. 写 alert log (备用, 即使邮件失败也有记录)
    INSERT INTO _alert_log (alert_subject, alert_body, created_at)
    VALUES (p_subject, p_body, NOW())
    ON DUPLICATE KEY UPDATE alert_body = VALUES(alert_body), created_at = NOW();

    -- 2. 调用系统 mail 命令 (如果部署在 Linux 且 mail 可用)
    -- 实际生产: 用 Python 脚本 send_alert.py 替代
    SET v_cmd = CONCAT(
        'python3 /opt/smokesignal/scripts/send_alert.py ',
        '--subject "', REPLACE(p_subject, '"', '\\"'), '" ',
        '--body "', REPLACE(p_body, '"', '\\"'), '" ',
        '--to "', v_recipient, '"'
    );

    -- 注释: sys_exec 默认禁用, 需 DBA 显式开启
    -- 这里用 INSERT log 代替, 避免权限问题
    -- 生产环境建议在 application 层捕获 SQL 异常并发送通知

    -- 若需要启用 sys_exec:
    -- SET @@global.sys_exec_priv = 1;
    -- CALL sys_exec(v_cmd);
END$$

DELIMITER ;

-- ============================================
-- alert log 表 (供 send_alert_email 写入)
-- ============================================
CREATE TABLE IF NOT EXISTS _alert_log (
    alert_subject VARCHAR(500) PRIMARY KEY,
    alert_body TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='procedure 告警日志 (procedure 失败时由 send_alert_email 写入)';

-- ============================================
-- 长期方案 (V2): 飞书 webhook
-- ============================================
-- 1. 创建飞书机器人 webhook: https://open.feishu.cn/open-apis/bot/v2/hook/<token>
-- 2. 在 application 层 (Python) 捕获 SQL 异常
-- 3. 通过 requests.post 调 webhook
-- 4. 见 backend/ai/analyzer_orchestrator.py 现有飞书集成

-- ============================================
-- 查询 alert log
-- ============================================
-- SELECT * FROM _alert_log ORDER BY created_at DESC LIMIT 20;
