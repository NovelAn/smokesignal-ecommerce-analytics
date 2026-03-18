"""
Data Extractor Tests
"""
import pytest
from backend.ai.data_extractor import (
    extract_chat_insights,
    smart_truncate,
    detect_rookie_signal,
    detect_expert_signal,
    identify_question_type
)


class TestDataExtractor:
    """测试数据提取器"""

    def test_detect_rookie_signal(self):
        """测试新手信号检测"""
        # 新手信号
        assert detect_rookie_signal("我是新手，不懂怎么选") == True
        assert detect_rookie_signal("求推荐一款适合入门的") == True
        assert detect_rookie_signal("第一次买，请指导") == True

        # 非新手信号
        assert detect_rookie_signal("这款的finish怎么样") == False
        assert detect_rookie_signal("发货了吗") == False

    def test_detect_expert_signal(self):
        """测试专家信号检测"""
        # 专家信号
        assert detect_expert_signal("这款的finish是什么") == True
        assert detect_expert_signal("briar的grain怎么样") == True
        assert detect_expert_signal("产地和工艺细节") == True

        # 非专家信号
        assert detect_expert_signal("我是新手") == False
        assert detect_expert_signal("多少钱") == False

    def test_identify_question_type(self):
        """测试问题类型识别"""
        assert identify_question_type("推荐一款适合新手的") == "售前咨询"
        assert identify_question_type("这个怎么用") == "使用指导"
        assert identify_question_type("多少钱") == "价格询问"
        assert identify_question_type("什么时候发货") == "物流咨询"
        assert identify_question_type("坏了怎么办") == "售后问题"

    def test_smart_truncate(self):
        """测试智能截取"""
        # 短文本不截取
        short_text = "这是一段短文本"
        assert smart_truncate(short_text, 500) == short_text

        # 包含关键词的长文本完整保留
        long_text_with_keyword = "我是新手" + "的内容" * 200
        result = smart_truncate(long_text_with_keyword, 500)
        assert "我是新手" in result

        # 普通长文本截取
        long_text = "这是一段很长的文本" * 100
        result = smart_truncate(long_text, 500)
        assert len(result) <= 550  # 允许一些误差
        assert "..." in result

    def test_extract_chat_insights(self):
        """测试聊天记录提取"""
        chats = [
            {
                "sender_nick": "test_user",
                "content": "我是新手，求推荐",
                "msg_time": "2026-01-29 10:00:00"
            },
            {
                "sender_nick": "test_user",
                "content": "这款的finish怎么样",
                "msg_time": "2026-01-29 10:05:00"
            }
        ]

        insights = extract_chat_insights(chats)

        assert "完整对话" in insights
        assert "新手信号" in insights
        assert "专家信号" in insights
        assert len(insights["新手信号"]) == 1
        assert len(insights["专家信号"]) == 1
        assert len(insights["完整对话"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
