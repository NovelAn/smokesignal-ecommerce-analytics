-- Separate customer-service state for Priority and Inventory workflows.
SET @has_workstream := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'customer_service_log'
      AND COLUMN_NAME = 'workstream'
);
SET @add_workstream := IF(
    @has_workstream = 0,
    "ALTER TABLE customer_service_log ADD COLUMN workstream VARCHAR(32) NOT NULL DEFAULT 'priority' AFTER buyer_nick",
    'SELECT 1'
);
PREPARE add_workstream_stmt FROM @add_workstream;
EXECUTE add_workstream_stmt;
DEALLOCATE PREPARE add_workstream_stmt;

UPDATE customer_service_log
SET workstream = 'priority'
WHERE workstream IS NULL OR workstream = '';

SET @has_unique_workstream := (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'customer_service_log'
      AND INDEX_NAME = 'uk_customer_service_workstream'
);
SET @add_unique_workstream := IF(
    @has_unique_workstream = 0,
    'ALTER TABLE customer_service_log ADD UNIQUE KEY uk_customer_service_workstream (buyer_nick, workstream)',
    'SELECT 1'
);
PREPARE add_unique_workstream_stmt FROM @add_unique_workstream;
EXECUTE add_unique_workstream_stmt;
DEALLOCATE PREPARE add_unique_workstream_stmt;
