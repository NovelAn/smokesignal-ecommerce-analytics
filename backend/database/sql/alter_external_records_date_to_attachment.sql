-- 场外信息表增加日期范围和附件字段
ALTER TABLE external_records
  ADD COLUMN date_to DATE COMMENT '结束日期（为空表示单日记录）' AFTER record_date,
  ADD COLUMN attachment_url VARCHAR(500) COMMENT '附件图片路径' AFTER category;
