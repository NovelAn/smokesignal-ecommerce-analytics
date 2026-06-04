-- ============================================
-- maintain_history_partitions procedure
-- ============================================
-- 用途：每月 1 号 00:00 自动滚动 partition
--   1. 添加下个月 partition (p_nextMM, 从 p_future 拆分)
--   2. 删除超过 24M 的 partition (按 snapshot_date 范围)
-- 幂等：检查 partition 是否存在，存在则跳过添加
-- 告警：失败时发邮件
-- ============================================

DROP PROCEDURE IF EXISTS maintain_history_partitions;

DELIMITER $$

CREATE PROCEDURE maintain_history_partitions()
BEGIN
    DECLARE v_next_month DATE DEFAULT DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01');
    DECLARE v_next_month_end DATE DEFAULT DATE_ADD(v_next_month, INTERVAL 1 MONTH);
    DECLARE v_new_partition VARCHAR(20);
    DECLARE v_old_partition VARCHAR(20);
    DECLARE v_cutoff DATE DEFAULT DATE_SUB(CURDATE(), INTERVAL 24 MONTH);
    DECLARE v_cutoff_partition VARCHAR(20);
    DECLARE v_old_pname VARCHAR(20);
    DECLARE v_old_pdesc TEXT;
    DECLARE v_done INT DEFAULT 0;
    DECLARE v_error_msg TEXT DEFAULT NULL;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        GET DIAGNOSTICS CONDITION 1 v_error_msg = MESSAGE_TEXT;
        CALL send_alert_email(
            '[smokesignal] maintain_history_partitions 失败',
            CONCAT('error: ', v_error_msg)
        );
        RESIGNAL;
    END;

    SELECT CONCAT('开始 partition 维护, cutoff=', v_cutoff) AS message;

    -- ============================================
    -- Step 1: 添加下个月 partition
    -- ============================================
    SET v_new_partition = CONCAT('p', DATE_FORMAT(v_next_month, '%Y%m'));

    -- 检查 partition 是否已存在
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.PARTITIONS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'target_buyers_precomputed_history'
          AND PARTITION_NAME = v_new_partition
    ) THEN
        SET @sql_add = CONCAT(
            'ALTER TABLE target_buyers_precomputed_history REORGANIZE PARTITION p_future INTO (',
            'PARTITION ', v_new_partition, ' VALUES LESS THAN (TO_DAYS(''', DATE_FORMAT(v_next_month_end, '%Y-%m-%d'), ''')),',
            'PARTITION p_future VALUES LESS THAN MAXVALUE)'
        );
        PREPARE stmt FROM @sql_add;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SELECT CONCAT('添加 partition: ', v_new_partition) AS message;
    ELSE
        SELECT CONCAT('partition 已存在, 跳过: ', v_new_partition) AS message;
    END IF;

    -- ============================================
    -- Step 2: 删除超过 24M 的 partition
    -- ============================================
    -- 24M cutoff = 2024-MM-DD, drop 所有 PARTITION_DESCRIPTION < cutoff_to_days
    SET v_cutoff_partition = CONCAT('p', DATE_FORMAT(v_cutoff, '%Y%m'));

    -- 遍历 information_schema, drop 所有 PARTITION_DESCRIPTION < TO_DAYS(cutoff+1day) 的 partition
    -- (因为 partition 是 < X, 所以 cutoff = 24M 前最后一个月应该被 drop)
    BEGIN
        DECLARE cur CURSOR FOR
            SELECT PARTITION_NAME, PARTITION_DESCRIPTION
            FROM information_schema.PARTITIONS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'target_buyers_precomputed_history'
              AND PARTITION_NAME != 'p_future'
              AND PARTITION_DESCRIPTION != 'MAXVALUE'
              AND CAST(PARTITION_DESCRIPTION AS UNSIGNED) < TO_DAYS(v_cutoff)
            ORDER BY PARTITION_ORDINAL_POSITION;

        DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

        OPEN cur;
        drop_loop: LOOP
            FETCH cur INTO v_old_pname, v_old_pdesc;
            IF v_done THEN
                LEAVE drop_loop;
            END IF;

            SET @sql_drop = CONCAT(
                'ALTER TABLE target_buyers_precomputed_history DROP PARTITION ', v_old_pname
            );
            PREPARE stmt FROM @sql_drop;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            SELECT CONCAT('删除 partition: ', v_old_pname) AS message;
        END LOOP;
        CLOSE cur;
    END;

    SELECT 'partition 维护完成' AS message;
END$$

DELIMITER ;

-- ============================================
-- 注册事件: 每月 1 号 00:00
-- ============================================
DROP EVENT IF EXISTS event_maintain_history_partitions;

CREATE EVENT event_maintain_history_partitions
ON SCHEDULE EVERY 1 MONTH
STARTS CONCAT(CURDATE() + INTERVAL 1 DAY - INTERVAL DAYOFMONTH(CURDATE()) DAY, ' 00:00:00')
COMMENT '每月 1 号 00:00 维护 history partition (add new + drop >24M)'
DO
CALL maintain_history_partitions();

-- ============================================
-- 手动测试
-- ============================================
-- CALL maintain_history_partitions();
