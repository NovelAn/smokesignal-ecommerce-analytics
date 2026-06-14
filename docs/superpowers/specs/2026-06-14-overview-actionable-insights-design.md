# Overview 可行动洞察设计

**日期：** 2026-06-14

## 目标

解决 Overview 中三个问题：VIC 群体画像标签重复且缺少结论；库存需求不能记录客服处理；顶部指标缺少数据时间说明，关键词仍读取 2026-03-24 的陈旧缓存。

## VIC 群体画像

后端新增确定性的语义主题归并层，不再直接返回数百个原始标签：

- 兴趣主题：复购行为、活动驱动、正价与品质、成衣偏好、烟具偏好、鞋履偏好、配饰偏好、跨品类探索、静默购买与批量采购。
- 痛点主题：复购不足与流失、互动数据不足、VIP 权益错配、折扣依赖、品类集中、退款退货、尺码版型、服务与履约。

同一客户的多个近义标签在同一主题内只计一次。例如“成衣主导”“男士成衣主导”“梭织外套”“KNITWEAR”统一贡献给“成衣偏好”。

API 保持 key_interests、key_pain_points 基础结构，为每个主题增加 examples。新增 summary.headline、summary.bullets、raw_label_count 和 aggregated_theme_count。

前端只展示主要主题和三条群体总结，不再提供展开全部原始标签。

## 库存客服闭环

复用 PriorityList 的 pending、contacted、resolved 状态语义，但库存和 Priority 必须相互隔离。

customer_service_log 新增 workstream，值为 priority 或 inventory，并建立 buyer_nick + workstream 唯一键。现有记录全部保留并归为 priority。

service/mark 和批量接口增加可选 workstream，缺省仍为 priority。库存接口只返回未处理、pending，或客服处理后又出现新库存提问或新 AI 分析的客户，并返回库存 workstream 的客服状态。

## 关键词实时统计

keyword-analysis 增加 start_date 和 end_date，直接查询 chat_history：

- 仅统计客户发送的消息。
- 按 Overview 时间筛选过滤 msg_time。
- 客户类型通过 target_buyers_precomputed 关联。
- 分类规则复用 KEYWORD_CATEGORIES。
- 库存查询与其他分类统一使用消息命中统计口径。

响应新增 data_source=live、日期范围和 last_message_at。前端在时间筛选变化时重新请求并展示数据范围。

## 顶部指标

顶部四组指标保留“当前客户池状态”语义：

- 数据来自每日刷新的 target_buyers_precomputed。
- 情感优先使用 buyer_ai_analysis_cache 的最新值。
- 前端显示“当前运营快照 · 更新于 …”，明确不受趋势时间筛选影响。
- 时间选择器改名为“趋势与沟通分析周期”。

## 数据迁移

迁移脚本添加 workstream、保留并标记现有记录为 priority，在确认无重复后添加复合唯一键。迁移不删除记录、不修改客户数据、不变更凭据。

## 验收

- VIC 测试覆盖同义归并、单客户主题去重、summary 和空数据。
- 库存测试覆盖 workstream 隔离、处理后隐藏、新提问重新激活。
- 关键词测试覆盖时间与客户类型过滤。
- Dashboard 测试验证最新 AI 情感和快照时间。
- Playwright 验证 VIC 总结、库存状态按钮、关键词时间变化与快照说明。

