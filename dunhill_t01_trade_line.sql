-- dunhill.dunhill_t01_trade_line source

CREATE OR REPLACE
ALGORITHM = UNDEFINED VIEW `dunhill_t01_trade_line` AS
select
    (case
        when ((`merge_orders`.`店铺名称` like '%小程序%')
        or (`merge_orders`.`店铺名称` like '%官方商城%')) then 'DTC'
        else 'PFS'
    end) AS `channel`,
    `merge_orders`.`店铺名称` AS `店铺名称`,
    `merge_orders`.`订单号` AS `订单号`,
    `merge_orders`.`子订单号` AS `子订单号`,
    `merge_orders`.`买家昵称` AS `买家昵称`,
    `merge_orders`.`买家openid` AS `买家openid`,
    `merge_orders`.`client_monthly_tag` AS `client_monthly_tag`,
    `merge_orders`.`平台创建时间` AS `平台创建时间`,
    `merge_orders`.`付款时间` AS `付款时间`,
    `merge_orders`.`付款日期` AS `付款日期`,
    `merge_orders`.`最后付款时间` AS `最后付款时间`,
    `merge_orders`.`子订单状态` AS `子订单状态`,
    `merge_orders`.`图片地址` AS `图片地址`,
    `merge_orders`.`是否聚划算` AS `是否聚划算`,
    `merge_orders`.`预售单状态` AS `预售单状态`,
    `merge_orders`.`天猫ID` AS `天猫ID`,
    `merge_orders`.`天猫商品编码` AS `天猫商品编码`,
    `merge_orders`.`天猫款号` AS `天猫款号`,
    `merge_orders`.`天猫外部编码` AS `天猫外部编码`,
    `merge_orders`.`条形码` AS `条形码`,
    `merge_orders`.`商品名称` AS `商品名称`,
    `merge_orders`.`宝尊商品编码` AS `宝尊商品编码`,
    `merge_orders`.`件数` AS `件数`,
    `merge_orders`.`商品划线价` AS `商品划线价`,
    `merge_orders`.`划线价总金额` AS `划线价总金额`,
    `merge_orders`.`优惠金额` AS `优惠金额`,
    `merge_orders`.`应付总金额` AS `应付总金额`,
    `merge_orders`.`成交单价` AS `成交单价`,
    `merge_orders`.`成交总金额` AS `成交总金额`,
    `merge_orders`.`省份` AS `省份`,
    `merge_orders`.`城市` AS `城市`,
    `merge_orders`.`退款类型` AS `退款类型`,
    `merge_orders`.`退款金额` AS `退款金额`,
    `merge_orders`.`退款完结时间` AS `退款完结时间`,
    `merge_orders`.`退款完结日期` AS `退款完结日期`,
    `merge_orders`.`退款原因` AS `退款原因`,
    `merge_orders`.`商品sku属性` AS `商品sku属性`,
    `p`.`skc` AS `skc`,
    `p`.`product_name` AS `product_name`,
    `price`.`rsp` AS `rsp`,
    `p`.`oms_category` AS `oms_category`,
    `p`.`category` AS `category`,
    `p`.`main_category` AS `main_category`,
    `p`.`division` AS `division`,
    `p`.`season_by_arrival` AS `season_by_arrival`,
    `p`.`season_by_code` AS `season_by_code`,
    `p`.`commercial_line` AS `commercial_line`,
    (case
        when ((((`merge_orders`.`成交单价` / `price`.`rsp`) < 0.9)
        and (`merge_orders`.`天猫外部编码` <> 'DUHA2106'))
        or (`merge_orders`.`天猫款号` in ('DU19FL1200W', 'DU22RL27800'))) then 'MD'
        else 'FP'
    end) AS `FP_MD`,
    `fq`.`是否分期` AS `是否分期`,
    `fq`.`分期数` AS `分期数`,
    `fq`.`是否免息` AS `是否免息`,
    (case
        when (`ls_order`.`场次ID` is null) then 0
        else 1
    end) AS `livestream_flag`,
    `ls_order`.`场次ID` AS `直播场次ID`,
    `ls_order`.`直播场次标题` AS `直播场次标题`,
    `ls_order`.`开播时间` AS `直播开播时间`,
    `ls_order`.`确认收货时间` AS `直播确认收货时间`,
    `ls_order`.`确认收货金额` AS `直播确认收货金额`,
    (case
        when (`ff`.`平台对接码` is null) then 0
        else 1
    end) AS `ff_flag`,
    (case
        when (`sc`.`订单号` is null) then 0
        else 1
    end) AS `sc_flag`,
    `sc`.`推广来源` AS `sc来源`,
    `sc`.`推广日期区间` AS `sc推广日期`,
    `jda`.`PayYear` AS `pay_year`,
    `jda`.`PaySeason` AS `pay_season`,
    `jda`.`PayMonth` AS `pay_month`,
    `jda`.`PayWeek` AS `pay_week`
from
    ((((((((
    select
        `o`.`店铺名称` AS `店铺名称`,
        `o`.`订单号` AS `订单号`,
        `o`.`子订单号` AS `子订单号`,
        `o`.`买家昵称` AS `买家昵称`,
        `o`.`买家openid` AS `买家openid`,
        `o`.`平台创建时间` AS `平台创建时间`,
        `o`.`付款时间` AS `付款时间`,
        cast(`o`.`付款时间` as date) AS `付款日期`,
        `o`.`最后付款时间` AS `最后付款时间`,
        `o`.`子订单状态` AS `子订单状态`,
        `o`.`图片地址` AS `图片地址`,
        `o`.`是否聚划算` AS `是否聚划算`,
        `o`.`预售单状态` AS `预售单状态`,
        `o`.`天猫ID` AS `天猫ID`,
        `o`.`天猫商品编码` AS `天猫商品编码`,
        `o`.`天猫款号` AS `天猫款号`,
        `o`.`天猫外部编码` AS `天猫外部编码`,
        `o`.`条形码` AS `条形码`,
        `o`.`商品名称` AS `商品名称`,
        `o`.`宝尊商品编码` AS `宝尊商品编码`,
        `o`.`件数` AS `件数`,
        `o`.`商品划线价` AS `商品划线价`,
        `o`.`划线价总金额` AS `划线价总金额`,
        `o`.`优惠金额` AS `优惠金额`,
        `o`.`应付总金额` AS `应付总金额`,
        `o`.`成交单价` AS `成交单价`,
        `o`.`成交总金额` AS `成交总金额`,
        `o`.`省份` AS `省份`,
        `o`.`城市` AS `城市`,
        `rfd`.`是否需要退货` AS `退款类型`,
        `rfd`.`买家退款金额` AS `退款金额`,
        `rfd`.`退款完结时间` AS `退款完结时间`,
        cast(`rfd`.`退款完结时间` as date) AS `退款完结日期`,
        `rfd`.`买家退款原因` AS `退款原因`,
        `rfd`.`退款状态` AS `退款状态`,
        `o`.`商品sku属性` AS `商品sku属性`,
        `o`.`client_monthly_tag` AS `client_monthly_tag`
    from
        (`dunhill_bi订单源` `o`
    left join (
        select
            `dunhill_tm退款源`.`订单编号` AS `订单编号`,
            `dunhill_tm退款源`.`退款编号` AS `退款编号`,
            `dunhill_tm退款源`.`支付宝交易号` AS `支付宝交易号`,
            `dunhill_tm退款源`.`订单付款时间` AS `订单付款时间`,
            `dunhill_tm退款源`.`商品id` AS `商品id`,
            `dunhill_tm退款源`.`商品编码` AS `商品编码`,
            `dunhill_tm退款源`.`退款完结时间` AS `退款完结时间`,
            `dunhill_tm退款源`.`买家会员名称` AS `买家会员名称`,
            `dunhill_tm退款源`.`买家实际支付金额` AS `买家实际支付金额`,
            `dunhill_tm退款源`.`宝贝标题` AS `宝贝标题`,
            `dunhill_tm退款源`.`买家退款金额` AS `买家退款金额`,
            `dunhill_tm退款源`.`手工退款` AS `手工退款`,
            `dunhill_tm退款源`.`是否需要退货` AS `是否需要退货`,
            `dunhill_tm退款源`.`退款的申请时间` AS `退款的申请时间`,
            `dunhill_tm退款源`.`超时时间` AS `超时时间`,
            `dunhill_tm退款源`.`退款状态` AS `退款状态`,
            `dunhill_tm退款源`.`货物状态` AS `货物状态`,
            `dunhill_tm退款源`.`退货物流信息` AS `退货物流信息`,
            `dunhill_tm退款源`.`发货物流信息` AS `发货物流信息`,
            `dunhill_tm退款源`.`客服介入状态` AS `客服介入状态`,
            `dunhill_tm退款源`.`卖家真实姓名` AS `卖家真实姓名`,
            `dunhill_tm退款源`.`卖家退货地址` AS `卖家退货地址`,
            `dunhill_tm退款源`.`卖家邮编` AS `卖家邮编`,
            `dunhill_tm退款源`.`卖家电话` AS `卖家电话`,
            `dunhill_tm退款源`.`卖家手机` AS `卖家手机`,
            `dunhill_tm退款源`.`退货物流单号` AS `退货物流单号`,
            `dunhill_tm退款源`.`退货物流公司` AS `退货物流公司`,
            `dunhill_tm退款源`.`买家退款原因` AS `买家退款原因`,
            `dunhill_tm退款源`.`买家退款说明` AS `买家退款说明`,
            `dunhill_tm退款源`.`买家退货时间` AS `买家退货时间`,
            `dunhill_tm退款源`.`责任方` AS `责任方`,
            `dunhill_tm退款源`.`售中或售后` AS `售中或售后`,
            `dunhill_tm退款源`.`商家备注` AS `商家备注`,
            `dunhill_tm退款源`.`完结时间` AS `完结时间`,
            `dunhill_tm退款源`.`部分退款` AS `部分退款`,
            `dunhill_tm退款源`.`审核操作人` AS `审核操作人`,
            `dunhill_tm退款源`.`举证超时` AS `举证超时`,
            `dunhill_tm退款源`.`是否零秒响应` AS `是否零秒响应`,
            `dunhill_tm退款源`.`退款操作人` AS `退款操作人`,
            `dunhill_tm退款源`.`退款原因标签` AS `退款原因标签`,
            `dunhill_tm退款源`.`业务类型` AS `业务类型`
        from
            `dunhill_tm退款源`
        where
            ((`dunhill_tm退款源`.`退款状态` <> '退款关闭')
                or (`dunhill_tm退款源`.`退款状态` is null))) `rfd` on
        (((`o`.`订单号` = `rfd`.`订单编号`)
            and (`o`.`天猫商品编码` = `rfd`.`商品编码`))))
    where
        ((`o`.`成交总金额` > 1)
            and (`o`.`付款时间` is not null))
union
    select
        `do`.`店铺名称` AS `店铺名称`,
        `do`.`订单号` AS `订单号`,
        `do`.`子订单号` AS `子订单号`,
        `do`.`买家昵称` AS `买家昵称`,
        `do`.`买家昵称` AS `买家openid`,
        `do`.`平台创建时间` AS `平台创建时间`,
        `do`.`付款时间` AS `付款时间`,
        cast(`do`.`付款时间` as date) AS `付款日期`,
        `do`.`最后付款时间` AS `最后付款时间`,
        `do`.`子订单状态` AS `子订单状态`,
        `do`.`图片地址` AS `图片地址`,
        `do`.`是否聚划算` AS `是否聚划算`,
        `do`.`预售单状态` AS `预售单状态`,
        `do`.`天猫ID` AS `天猫ID`,
        `do`.`天猫商品编码` AS `天猫商品编码`,
        `do`.`天猫款号` AS `天猫款号`,
        `do`.`天猫外部编码` AS `天猫外部编码`,
        `do`.`条形码` AS `条形码`,
        `do`.`商品名称` AS `商品名称`,
        `do`.`宝尊商品编码` AS `宝尊商品编码`,
        `do`.`件数` AS `件数`,
        `do`.`商品划线价` AS `商品划线价`,
        `do`.`划线价总金额` AS `划线价总金额`,
        `do`.`优惠金额` AS `优惠金额`,
        `do`.`应付总金额` AS `应付总金额`,
        `do`.`成交单价` AS `成交单价`,
        `do`.`成交总金额` AS `成交总金额`,
        `do`.`省份` AS `省份`,
        `do`.`城市` AS `城市`,
        `d_rfd`.`退款类型` AS `退款类型`,
        `d_rfd`.`退款金额` AS `退款金额`,
        `d_rfd`.`退款完结时间` AS `退款完结时间`,
        cast(`d_rfd`.`退款完结时间` as date) AS `退款完结日期`,
        `d_rfd`.`退款类型` AS `退款原因`,
        `d_rfd`.`退款状态` AS `退款状态`,
        `do`.`商品sku属性` AS `商品sku属性`,
        `do`.`client_monthly_tag` AS `client_monthly_tag`
    from
        (`dunhill_dtc订单源_hive` `do`
    left join (
        select
            `dunhill_dtc退款源_hive`.`店铺ID` AS `店铺ID`,
            `dunhill_dtc退款源_hive`.`店铺名称` AS `店铺名称`,
            `dunhill_dtc退款源_hive`.`订单号` AS `订单号`,
            `dunhill_dtc退款源_hive`.`子订单号` AS `子订单号`,
            `dunhill_dtc退款源_hive`.`最后付款时间` AS `最后付款时间`,
            `dunhill_dtc退款源_hive`.`spu` AS `spu`,
            `dunhill_dtc退款源_hive`.`sku` AS `sku`,
            `dunhill_dtc退款源_hive`.`商品名称` AS `商品名称`,
            `dunhill_dtc退款源_hive`.`条形码` AS `条形码`,
            `dunhill_dtc退款源_hive`.`退款完结时间` AS `退款完结时间`,
            `dunhill_dtc退款源_hive`.`退款状态ID` AS `退款状态ID`,
            `dunhill_dtc退款源_hive`.`退款状态` AS `退款状态`,
            `dunhill_dtc退款源_hive`.`退款金额` AS `退款金额`,
            `dunhill_dtc退款源_hive`.`退款件数` AS `退款件数`,
            `dunhill_dtc退款源_hive`.`退款类型` AS `退款类型`,
            `dunhill_dtc退款源_hive`.`是否退货退款` AS `是否退货退款`
        from
            `dunhill_dtc退款源_hive`
        where
            ((`dunhill_dtc退款源_hive`.`退款状态` <> '退款关闭')
                or (`dunhill_dtc退款源_hive`.`退款状态` is null))) `d_rfd` on
        (((`do`.`订单号` = `d_rfd`.`订单号`)
            and (`do`.`子订单号` = `d_rfd`.`子订单号`))))
    where
        ((`do`.`成交总金额` > 1)
            and (`do`.`付款时间` is not null))) `merge_orders`
left join `dunhill_jda日历` `jda` on
    ((`merge_orders`.`付款日期` = `jda`.`PayDate`)))
left join `dunhill_pdt_info_by_sku` `p` on
    ((`merge_orders`.`天猫外部编码` = `p`.`sku`)))
left join `dunhill_tm订单分期购` `fq` on
    ((`merge_orders`.`订单号` = `fq`.`订单编号`)))
left join `dunhill_product_price` `price` on
    (((`merge_orders`.`天猫外部编码` = `price`.`平台对接码`)
        and (cast(`merge_orders`.`付款时间` as date) between `price`.`validFrom` and `price`.`validTo`))))
left join `dunhill_直播订单源` `ls_order` on
    ((`merge_orders`.`子订单号` = `ls_order`.`子订单ID`)))
left join `dunhill_dtc_ff_订单源` `ff` on
    (((`ff`.`平台订单号` = `merge_orders`.`订单号`)
        and (`ff`.`平台对接码` = `merge_orders`.`天猫外部编码`))))
left join `dunhill_dtc_sc_订单源` `sc` on
    ((`sc`.`订单号` = `merge_orders`.`订单号`)))
order by
    `merge_orders`.`付款日期`;