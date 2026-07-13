DROP TEMPORARY TABLE IF EXISTS failed_sentiment_batch_20260713;

CREATE TEMPORARY TABLE failed_sentiment_batch_20260713 (
    buyer_nick VARCHAR(255) PRIMARY KEY
);

INSERT INTO failed_sentiment_batch_20260713 (buyer_nick)
SELECT buyer_nick
FROM buyer_ai_analysis_cache
WHERE sentiment_analyzed_at BETWEEN '2026-07-13 15:48:37' AND '2026-07-13 15:50:40'
  AND sentiment_method = 'minimax_m3'
  AND sentiment_label = 'Neutral'
  AND sentiment_score = 0.50;

SELECT COUNT(*) AS selected_count
FROM failed_sentiment_batch_20260713;

START TRANSACTION;

UPDATE target_buyers_precomputed AS tb
JOIN failed_sentiment_batch_20260713 AS failed
  ON failed.buyer_nick = tb.buyer_nick
SET tb.sentiment_label = NULL,
    tb.sentiment_score = NULL,
    tb.dominant_intent = NULL,
    tb.pre_sale_score = 0,
    tb.post_sale_score = 0;

UPDATE buyer_ai_analysis_cache AS cache
JOIN failed_sentiment_batch_20260713 AS failed
  ON failed.buyer_nick = cache.buyer_nick
SET cache.sentiment_score = NULL,
    cache.sentiment_label = NULL,
    cache.intent_distribution = NULL,
    cache.dominant_intent = NULL,
    cache.pre_sale_keywords = NULL,
    cache.post_sale_keywords = NULL,
    cache.complaint_count = 0,
    cache.sentiment_method = NULL,
    cache.sentiment_analyzed_at = NULL,
    cache.sentiment_analyzed_last_chat_date = NULL,
    cache.incremental_chat_count = 0,
    cache.incremental_chat_from_date = NULL,
    cache.incremental_chat_to_date = NULL,
    cache.incremental_sentiment_label = NULL,
    cache.incremental_sentiment_score = NULL,
    cache.incremental_sentiment_analyzed_at = NULL;

COMMIT;

SELECT COUNT(*) AS retryable_count
FROM failed_sentiment_batch_20260713 AS failed
JOIN buyer_ai_analysis_cache AS cache
  ON cache.buyer_nick = failed.buyer_nick
WHERE cache.sentiment_score IS NULL
  AND cache.sentiment_analyzed_at IS NULL
  AND cache.sentiment_analyzed_last_chat_date IS NULL;
