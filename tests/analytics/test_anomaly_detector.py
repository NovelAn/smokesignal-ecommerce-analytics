import pytest
from datetime import date, timedelta
from backend.analytics.anomaly_detector import AnomalyDetector


def test_detect_sentiment_negative_shift():
    detector = AnomalyDetector()
    mock = {
        "buyer_nick": "buyer_001", "vip_level": "V3",
        "last_purchase_date": "2026-04-15", "last_chat_date": "2026-05-20",
        "previous_sentiment": "Positive", "current_sentiment": "Negative"
    }
    anomalies = detector.detect_anomalies([mock])
    assert len(anomalies) == 1
    assert anomalies[0]["anomaly_type"] == "sentiment_negative"
    assert anomalies[0]["severity"] == "high"


def test_detect_purchase_interval_long():
    detector = AnomalyDetector()
    long_ago = (date.today() - timedelta(days=200)).isoformat()
    mock = {"buyer_nick": "b2", "vip_level": "V2", "last_purchase_date": long_ago,
            "previous_sentiment": "Positive", "current_sentiment": "Positive"}
    anomalies = detector.detect_anomalies([mock])
    assert len(anomalies) == 1
    assert anomalies[0]["anomaly_type"] == "purchase_interval_long"


def test_detect_chat_frequency_drop():
    detector = AnomalyDetector()
    mock = {"buyer_nick": "b4", "vip_level": "V1",
            "current_month_chats": 3, "avg_monthly_chats": 20,
            "previous_sentiment": "Positive", "current_sentiment": "Positive"}
    anomalies = detector.detect_anomalies([mock])
    assert any(a["anomaly_type"] == "chat_frequency_drop" for a in anomalies)


def test_no_anomaly_for_normal():
    detector = AnomalyDetector()
    recent = (date.today() - timedelta(days=30)).isoformat()
    mock = {"buyer_nick": "b3", "vip_level": "V1", "last_purchase_date": recent,
            "previous_sentiment": "Positive", "current_sentiment": "Positive"}
    assert len(detector.detect_anomalies([mock])) == 0
