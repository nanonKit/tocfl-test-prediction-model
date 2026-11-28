-- which topics of Band A vocabulary the mock tests actually use

SELECT
    topic,
    COUNT(*)                                                       AS n_words,
    ROUND(100.0 * COUNT(*) FILTER (WHERE n_sets > 0) / COUNT(*), 1)  AS pct_seen,
    ROUND(100.0 * COUNT(*) FILTER (WHERE n_sets >= 3) / COUNT(*), 1) AS pct_3plus_sets,
    SUM(n_tokens)                                                  AS n_tokens,
    ROUND(100.0 * SUM(n_tokens) / SUM(SUM(n_tokens)) OVER (), 1)   AS pct_of_tokens
FROM mart_word_freq
WHERE is_band_a
GROUP BY topic
ORDER BY pct_seen DESC;