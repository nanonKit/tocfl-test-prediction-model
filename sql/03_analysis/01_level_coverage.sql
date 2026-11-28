-- how much of each level's vocabulary actually appears in the mock tests
-- Use   : decides study priority — levels with high pct_seen = learn every word,
--         low pct_seen = learn only the words the model ranks high

SELECT
    level,
    is_band_a,
    COUNT(*)                                              AS total_words,
    COUNT(*) FILTER (WHERE n_sets > 0)                    AS seen_words,
    ROUND(100.0 * seen_words / total_words, 1)            AS pct_seen,
    COUNT(*) FILTER (WHERE n_sets >= 3)                   AS seen_3plus_sets,
    ROUND(100.0 * seen_3plus_sets / total_words, 1)       AS pct_3plus_sets
FROM mart_word_freq
GROUP BY level, is_band_a
ORDER BY MIN(level_order);