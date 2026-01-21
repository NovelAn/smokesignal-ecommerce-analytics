"""
Utility functions for datetime parsing and formatting
"""
from datetime import datetime
from typing import Any, Optional


def parse_datetime(value: Any) -> Optional[datetime]:
    """
    Safely parse datetime from string or datetime object

    Args:
        value: String or datetime object to parse

    Returns:
        Datetime object or None if parsing fails
    """
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            # Handle ISO format with various separators
            return datetime.fromisoformat(value.replace('T', ' ').replace('Z', ''))
        except (ValueError, AttributeError):
            return None

    return None


def format_last_active(last_purchase: Any, last_chat: Any) -> str:
    """
    Format last active time for display

    Args:
        last_purchase: Last purchase datetime (string or datetime)
        last_chat: Last chat datetime (string or datetime)

    Returns:
        Formatted string like "Today", "Yesterday", "X Days ago", or "YYYY-MM-DD"
    """
    from datetime import datetime as dt

    now = dt.now()
    last_chat_parsed = parse_datetime(last_chat)
    last_purchase_parsed = parse_datetime(last_purchase)

    if last_chat_parsed:
        days = (now - last_chat_parsed).days
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        elif days < 30:
            return f"{days} Days ago"
        else:
            return last_chat_parsed.strftime("%Y-%m-%d")

    if last_purchase_parsed:
        return last_purchase_parsed.strftime("%Y-%m-%d")

    return "Unknown"
