"""
关键词分类词典
用于客户聊天记录的关键词提取和分类

规则：
1. 所有关键词必须是2个字及以上，避免单字歧义
2. 只使用语义明确、不易产生歧义的关键词
3. 避免使用太宽泛的词（如"免费"、"问题"等）

9个大类：
1. 赠品 - 赠品、小样、试用装、满赠
2. 包装 - 包装、礼盒、袋子、礼袋
3. 维修保养 - 维修、保养、清洗、售后
4. 退换货 - 退货、换货、退款
5. 产品推荐咨询 - 推荐、哪个好、怎么选
6. 产品参数咨询 - 尺寸、口径、规格、直径
7. 价格 - 价格、优惠、折扣、活动
8. 物流 - 发货、快递、到货、顺丰
9. 投诉反馈 - 投诉、差评、质量问题
"""

# 关键词分类词典（所有关键词必须>=2个字，且语义明确）
KEYWORD_CATEGORIES = {
    "赠品": [
        # 明确的赠品相关词
        "赠品", "小样", "试用装", "满赠", "满送",
        "活动赠品", "有赠品", "送赠品", "有赠吗"
    ],
    "包装": [
        # 包装相关（包括送礼包装需求）
        "包装", "礼盒", "袋子", "礼袋", "包装盒",
        "礼品袋", "手提袋", "包装袋", "礼盒装", "送礼盒",
        "有礼盒", "有盒子", "有袋子", "送人用"
    ],
    "维修保养": [
        # 维修保养服务
        "维修", "保养", "清洗", "清洁", "售后",
        "修理", "维护", "坏了", "损坏", "保修",
        "故障", "不能用了", "需要维修"
    ],
    "退换货": [
        # 退换货相关
        "退货", "换货", "退款", "退换", "退回",
        "换一个", "退了", "换一下", "申请退货",
        "想换", "要换", "换个", "退换货"
    ],
    "产品推荐咨询": [
        # 产品咨询和推荐
        "推荐", "哪个好", "怎么选", "适合", "介绍",
        "有什么区别", "建议", "款式", "推荐一下",
        "推荐款", "哪款好", "哪款", "帮我选"
    ],
    "产品参数咨询": [
        # 产品参数和规格
        "尺寸", "大小", "口径", "规格", "直径",
        "长度", "高度", "宽度", "重量", "参数",
        "多大", "多重", "多长", "多少目"
    ],
    "价格": [
        # 价格和优惠活动
        "价格", "多少钱", "优惠", "折扣", "便宜",
        "活动", "促销", "满减", "优惠券", "会员价",
        "打折", "降价", "差价", "有优惠", "有折扣",
        "有活动", "活动价"
    ],
    "物流": [
        # 物流配送
        "发货", "快递", "物流", "顺丰", "到货",
        "收到", "什么时候到", "配送", "运单",
        "什么时候发", "发快递", "几天到", "多久到"
    ],
    "投诉反馈": [
        # 投诉和负面反馈
        "投诉", "差评", "质量问题", "瑕疵", "缺陷",
        "做工", "粗糙", "服务差", "质量差", "很失望",
        "太慢了", "态度差"
    ]
}

# 分类列表（保持顺序）
CATEGORY_LIST = list(KEYWORD_CATEGORIES.keys())

# 反向映射：关键词 -> 分类
KEYWORD_TO_CATEGORY = {}
for category, keywords in KEYWORD_CATEGORIES.items():
    for keyword in keywords:
        KEYWORD_TO_CATEGORY[keyword] = category


def categorize_text(text: str) -> dict:
    """
    对文本进行分类，返回各分类的匹配结果

    Args:
        text: 待分类的文本

    Returns:
        {
            "赠品": ["赠品", "送"],
            "物流": ["发货"],
            ...
        }
    """
    if not text:
        return {}

    result = {}
    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword in text:
            if category not in result:
                result[category] = []
            result[category].append(keyword)

    return result


def extract_keywords(text: str) -> list:
    """
    从文本中提取所有匹配的关键词

    Args:
        text: 待提取的文本

    Returns:
        [("赠品", "赠品"), ("物流", "发货"), ...]
    """
    if not text:
        return []

    result = []
    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword in text:
            result.append((category, keyword))

    return result


def get_category_for_keyword(keyword: str) -> str:
    """
    获取关键词所属的分类

    Args:
        keyword: 关键词

    Returns:
        分类名称，如果未找到返回 None
    """
    return KEYWORD_TO_CATEGORY.get(keyword)
