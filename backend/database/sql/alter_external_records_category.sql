-- 扩展 category 字段以支持多选品类（逗号分隔）
ALTER TABLE external_records MODIFY COLUMN category VARCHAR(200) COMMENT '商品品类（仅消费类型，多选逗号分隔）';
