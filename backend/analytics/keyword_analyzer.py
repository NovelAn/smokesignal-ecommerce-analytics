"""Live keyword analysis over a bounded set of customer chat messages."""

from collections import Counter
from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional

from backend.analytics.keyword_categories import CATEGORY_LIST, extract_keywords


class KeywordAnalyzer:
    """Apply the shared keyword dictionary with one message-level counting basis."""

    def analyze_messages(
        self,
        rows: Iterable[Dict[str, Any]],
        category: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        category_counts: Counter = Counter()
        keyword_counts: Counter = Counter()
        matched_messages = 0
        last_message_at = None

        for row in rows:
            content = str(row.get("content") or "").strip()
            if len(content) < 3 or content.startswith("http") or content.isdigit():
                continue
            matches = extract_keywords(content)
            if not matches:
                continue

            matched_messages += 1
            matched_categories = {matched_category for matched_category, _ in matches}
            category_counts.update(matched_categories)
            keyword_counts.update(set(matches))

            message_time = row.get("msg_time")
            if message_time and (last_message_at is None or message_time > last_message_at):
                last_message_at = message_time

        category_total = sum(category_counts.values())
        category_distribution = [
            {
                "name": name,
                "value": category_counts.get(name, 0),
                "percentage": round(category_counts.get(name, 0) / category_total * 100, 1)
                if category_total else 0.0,
            }
            for name in CATEGORY_LIST
        ]
        selected_keywords = [
            ((matched_category, keyword), count)
            for (matched_category, keyword), count in keyword_counts.items()
            if category is None or matched_category == category
        ]
        selected_keywords.sort(key=lambda item: (-item[1], item[0][1]))
        keyword_total = sum(count for _, count in selected_keywords)
        keywords = [
            {
                "text": keyword,
                "value": count,
                "percentage": round(count / keyword_total * 100, 1) if keyword_total else 0.0,
                "category": matched_category,
            }
            for ((matched_category, keyword), count) in selected_keywords[:limit]
        ]

        return {
            "category_distribution": category_distribution,
            "keywords": keywords,
            "total_messages": matched_messages,
            "last_message_at": self._format_time(last_message_at),
            "data_source": "chat_history_live",
        }

    @staticmethod
    def _format_time(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)
