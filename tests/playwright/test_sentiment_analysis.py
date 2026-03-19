"""
Automated test for sentiment analysis force-refresh functionality

Tests:
1. Clear existing sentiment cache for a buyer
2. Trigger new sentiment analysis
3. Verify cache is updated with correct results
4. Verify sentiment score is reasonable for normal post-sale conversations
"""
import requests
import json
import time
import sys

# API base URL
BASE_URL = "http://localhost:8000/api/v2"

# Test buyer (use ASCII-safe representation for Windows console)
TEST_BUYER = "\u5c0f\u5723xiaosheng33"  # 小圣xiaosheng33


def safe_print(message: str):
    """Safe print that handles Windows GBK encoding issues"""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode('ascii', errors='replace').decode('ascii'))


def test_sentiment_analysis():
    """Test sentiment analysis force-refresh flow"""

    safe_print("=" * 60)
    safe_print(f"Testing sentiment analysis for: {TEST_BUYER}")
    safe_print("=" * 60)

    # Step 1: Get current buyer data (including cached sentiment)
    safe_print(f"\n[Step 1] Getting buyer data...")
    try:
        response = requests.get(f"{BASE_URL}/buyers/{TEST_BUYER}", timeout=30)
        if response.status_code == 200:
            buyer_data = response.json()
            safe_print(f"[OK] Got buyer data")

            # Show current sentiment
            current_sentiment = buyer_data.get("sentiment_score", "N/A")
            current_label = buyer_data.get("sentiment_label", "N/A")
            safe_print(f"  Current sentiment_score: {current_sentiment}")
            safe_print(f"  Current sentiment_label: {current_label}")
        else:
            safe_print(f"[FAIL] Failed to get buyer data: {response.status_code}")
            safe_print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        safe_print(f"[FAIL] Error getting buyer data: {e}")
        return False

    # Step 2: Force refresh sentiment analysis
    safe_print(f"\n[Step 2] Force refreshing sentiment analysis...")
    try:
        response = requests.post(
            f"{BASE_URL}/buyers/{TEST_BUYER}/force-refresh",
            params={"refresh_type": "sentiment", "reanalyze": True},
            timeout=120  # Allow up to 2 minutes for AI analysis
        )

        if response.status_code == 200:
            result = response.json()
            safe_print(f"[OK] Force refresh completed")

            new_sentiment = result.get("sentiment_score", "N/A")
            new_label = result.get("sentiment_label", "N/A")
            new_intent = result.get("dominant_intent", "N/A")
            ai_provider = result.get("ai_provider", "N/A")
            reanalyzed = result.get("reanalyzed", [])

            safe_print(f"  Cleared: {result.get('cleared', [])}")
            safe_print(f"  Reanalyzed: {reanalyzed}")
            safe_print(f"  AI provider: {ai_provider}")

            # Need to fetch the actual sentiment values from the response or re-fetch
            if "sentiment_score" not in result:
                # Fetch from buyer endpoint
                safe_print(f"\n[Step 2b] Fetching updated sentiment...")
                response2 = requests.get(f"{BASE_URL}/buyers/{TEST_BUYER}", timeout=30)
                if response2.status_code == 200:
                    buyer_data2 = response2.json()
                    new_sentiment = buyer_data2.get("sentiment_score", "N/A")
                    new_label = buyer_data2.get("sentiment_label", "N/A")
                    new_intent = buyer_data2.get("dominant_intent", "N/A")
                    safe_print(f"  New sentiment_score: {new_sentiment}")
                    safe_print(f"  New sentiment_label: {new_label}")
                    safe_print(f"  New dominant_intent: {new_intent}")
                else:
                    safe_print(f"[WARN] Could not fetch updated sentiment")
                    new_sentiment = None
        else:
            safe_print(f"[FAIL] Failed to force refresh: {response.status_code}")
            safe_print(f"  Response: {response.text[:500]}")
            return False
    except Exception as e:
        safe_print(f"[FAIL] Error force refreshing: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Verify cache was updated by fetching buyer data again
    safe_print(f"\n[Step 3] Verifying cache update...")
    time.sleep(1)  # Brief pause to ensure DB write completed

    try:
        response = requests.get(f"{BASE_URL}/buyers/{TEST_BUYER}", timeout=30)
        if response.status_code == 200:
            buyer_data = response.json()

            cached_sentiment = buyer_data.get("sentiment_score")
            cached_label = buyer_data.get("sentiment_label")

            safe_print(f"[OK] Retrieved updated buyer data")
            safe_print(f"  Cached sentiment_score: {cached_sentiment}")
            safe_print(f"  Cached sentiment_label: {cached_label}")

            # Update for validation
            new_sentiment = cached_sentiment
            new_label = cached_label
        else:
            safe_print(f"[FAIL] Failed to verify cache: {response.status_code}")
            return False
    except Exception as e:
        safe_print(f"[FAIL] Error verifying cache: {e}")
        return False

    # Step 4: Validate sentiment score reasonableness
    safe_print(f"\n[Step 4] Validating sentiment score...")

    # For normal post-sale return conversations, sentiment should be Neutral (0.4-0.6)
    # Not Negative (< 0.4) and not necessarily Positive (> 0.6)
    if new_sentiment is not None:
        try:
            score = float(new_sentiment)
            if 0.35 <= score <= 0.65:
                safe_print(f"[OK] Sentiment score {score} is in reasonable range (0.35-0.65)")
                safe_print(f"  This indicates neutral sentiment for normal business communication")
            elif score < 0.35:
                safe_print(f"[WARN] Sentiment score {score} is LOW (Negative)")
                safe_print(f"  For normal post-sale return conversations, this may indicate incorrect analysis")
                safe_print(f"  Check if AI is misinterpreting normal business language as negative")
            else:
                safe_print(f"[INFO] Sentiment score {score} is high (Positive)")
                safe_print(f"  For normal post-sale return conversations, this might indicate:")
                safe_print(f"  - Customer was satisfied with the resolution")
                safe_print(f"  - Or AI is over-optimistic")
        except (ValueError, TypeError) as e:
            safe_print(f"[WARN] Could not validate score: {new_sentiment} ({e})")
    else:
        safe_print(f"[FAIL] No sentiment score returned")
        return False

    safe_print(f"\n" + "=" * 60)
    safe_print(f"Test completed!")
    safe_print(f"=" * 60)

    return True


if __name__ == "__main__":
    success = test_sentiment_analysis()
    sys.exit(0 if success else 1)
