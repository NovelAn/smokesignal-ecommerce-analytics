"""
FastAPI routes for buyer analytics API
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from backend.analytics import BuyerAnalyzer
from backend.ai import ZhipuClient
from backend.database import BuyerQueries

router = APIRouter()
analyzer = BuyerAnalyzer()
ai_client = ZhipuClient()


@router.get("/")
async def root():
    """API health check"""
    return {
        "status": "ok",
        "service": "SmokeSignal Analytics API",
        "version": "1.0.0"
    }


@router.get("/buyers")
async def get_all_buyers(
    limit: int = 100,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get list of buyer nicknames with pagination, date filtering and search

    Args:
        limit: Maximum number of buyers to return (default: 100)
        offset: Number of buyers to skip (for pagination)
        start_date: Filter buyers with orders after this date (format: YYYY-MM-DD)
        end_date: Filter buyers with orders before this date (format: YYYY-MM-DD)
        search: Search by nickname (partial match, case-insensitive)
    """
    try:
        buyers = analyzer.get_all_buyers(start_date, end_date, search, limit, offset)
        return buyers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/{user_nick}")
async def get_buyer_profile(user_nick: str, include_ai: bool = False) -> Dict[str, Any]:
    """
    Get complete buyer profile

    Args:
        user_nick: Buyer nickname
        include_ai: Whether to include AI analysis (slower)
    """
    try:
        # Get basic analysis
        profile = analyzer.analyze_buyer(user_nick)

        # Add AI analysis if requested
        if include_ai:
            profile = await _add_ai_analysis(profile)

        return profile

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/{user_nick}/orders")
async def get_buyer_orders(user_nick: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get buyer order history"""
    try:
        orders = analyzer._fetch_order_history(user_nick, limit)
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers/{user_nick}/chats")
async def get_buyer_chats(user_nick: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get buyer chat messages"""
    try:
        chats = analyzer.db.execute_query(
            BuyerQueries.get_chat_messages(user_nick, limit),
            (user_nick,)
        )
        return chats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/metrics")
async def get_dashboard_metrics() -> Dict[str, Any]:
    """Get dashboard overview metrics"""
    try:
        metrics = analyzer.get_dashboard_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/daily-stats")
async def get_daily_stats(days: int = 30) -> List[Dict[str, Any]]:
    """Get daily statistics for dashboard"""
    try:
        stats = analyzer.db.execute_query(BuyerQueries.get_daily_stats(days))
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/actionable-customers")
async def get_actionable_customers() -> List[Dict[str, Any]]:
    """
    Get actionable customers (priority board)
    Returns customers needing attention: churn risk, high value, etc.
    """
    try:
        # Get base data
        results = analyzer.db.execute_query(BuyerQueries.get_actionable_customers())

        actionable_list = []
        for customer in results:
            user_nick = customer["user_nick"]
            last_purchase = customer.get("last_purchase")
            last_chat = customer.get("last_chat")
            total_ltv = customer.get("total_ltv", 0)

            # Determine issue type and priority
            issue_type, priority, action = _determine_actionable_type(
                last_purchase, last_chat, total_ltv
            )

            if issue_type:
                actionable_list.append({
                    "id": str(len(actionable_list) + 1),
                    "user_nick": user_nick,
                    "issue_type": issue_type,
                    "last_active": _format_last_active(last_purchase, last_chat),
                    "priority": priority,
                    "status": "Pending",
                    "action_suggestion": action
                })

        return actionable_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buyers/{user_nick}/ai-analysis")
async def analyze_buyer_with_ai(user_nick: str) -> Dict[str, Any]:
    """
    Trigger AI analysis for a buyer
    Returns comprehensive AI-generated insights
    """
    try:
        # Get buyer profile
        profile = analyzer.analyze_buyer(user_nick)

        # Add AI analysis
        profile_with_ai = await _add_ai_analysis(profile)

        # Save AI analysis to database (optional - can be implemented later)
        # For now, just return it

        return profile_with_ai

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

async def _add_ai_analysis(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Add AI analysis to buyer profile"""
    user_nick = profile["user_nick"]

    # Prepare data for AI
    profile_data = profile["profile"]
    order_summary = _generate_order_summary(profile.get("order_history", []))
    recent_chats = profile.get("chat_metrics", {})

    # Get actual chat messages
    try:
        chat_messages = analyzer.db.execute_query(
            BuyerQueries.get_chat_messages(user_nick, 20),
            (user_nick,)
        )
    except:
        chat_messages = []

    # Call AI
    ai_analysis = ai_client.analyze_buyer_persona(
        user_nick,
        profile_data,
        chat_messages,
        order_summary
    )

    # Update profile with AI analysis
    profile["profile"]["analysis"] = ai_analysis

    # Also analyze intent if we have chat messages
    if chat_messages:
        messages_text = [msg.get("content", "") for msg in chat_messages if msg.get("content")]
        if messages_text:
            intent_distribution = ai_client.extract_intent_distribution(messages_text)
            # Convert to radar chart format
            profile["profile"]["intent_scores"] = [
                {"subject": intent, "A": count, "fullMark": max(intent_distribution.values(), default=1)}
                for intent, count in intent_distribution.items()
            ]

    return profile


def _generate_order_summary(order_history: List[Dict]) -> str:
    """Generate order summary for AI prompt"""
    if not order_history:
        return "暂无订单记录"

    summary_lines = []
    for order in order_history[:10]:  # Last 10 orders
        date = order.get("purchase_date", "")
        amount = order.get("net_amount", 0)
        category = order.get("category", "")
        price_type = "折扣品" if order.get("price_type") == "MD" else "正价品"
        summary_lines.append(f"- {date}: {category} ({price_type}), {amount:.2f}元")

    return "\n".join(summary_lines)


def _determine_actionable_type(
    last_purchase: Any,
    last_chat: Any,
    total_ltv: float
) -> tuple:
    """
    Determine if customer is actionable and what type

    Returns: (issue_type, priority, action_suggestion)
    """
    from datetime import datetime

    # Ensure total_ltv is a number
    if total_ltv is None:
        total_ltv = 0

    now = datetime.now()

    # Convert string to datetime if needed
    if isinstance(last_purchase, str):
        try:
            last_purchase = datetime.fromisoformat(last_purchase.replace('T', ' ').replace('Z', ''))
        except:
            last_purchase = None

    if isinstance(last_chat, str):
        try:
            last_chat = datetime.fromisoformat(last_chat.replace('T', ' ').replace('Z', ''))
        except:
            last_chat = None

    days_since_purchase = (now - last_purchase).days if last_purchase else 9999
    days_since_chat = (now - last_chat).days if last_chat else 9999

    # Churn risk
    if days_since_purchase > 730 and days_since_chat > 180:
        return ("Churn Risk", "High", "发送复购优惠重新激活")

    # High value but inactive
    if total_ltv >= 50000 and days_since_chat > 30:
        return ("High Value", "Medium", "VIP专属服务跟进")

    # Recent activity but no purchase
    if days_since_chat <= 7 and days_since_purchase > 90:
        return ("Gift Inquiry", "Low", "推荐合适产品")

    return None, None, None


def _format_last_active(last_purchase: Any, last_chat: Any) -> str:
    """Format last active time for display"""
    from datetime import datetime

    now = datetime.now()

    # Convert string to datetime if needed
    if isinstance(last_chat, str):
        try:
            last_chat = datetime.fromisoformat(last_chat.replace('T', ' ').replace('Z', ''))
        except:
            last_chat = None

    if isinstance(last_purchase, str):
        try:
            last_purchase = datetime.fromisoformat(last_purchase.replace('T', ' ').replace('Z', ''))
        except:
            last_purchase = None

    if last_chat:
        days = (now - last_chat).days
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        elif days < 30:
            return f"{days} Days ago"
        else:
            return last_chat.strftime("%Y-%m-%d")

    if last_purchase:
        return last_purchase.strftime("%Y-%m-%d")

    return "Unknown"
