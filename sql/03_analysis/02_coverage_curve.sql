-- coverage curve — learn the top-N Band A words (in mvp_rank order),

WITH ranked AS (
    SELECT
        mvp_rank,
        n_tokens,
        SUM(n_tokens) OVER (ORDER BY mvp_rank)                    AS cum_tokens
    FROM mart_word_freq
    WHERE is_band_a
),

totals AS (
    SELECT
        SUM(n_tokens)                                  AS all_tokens,       -- every matched token, any level
        SUM(n_tokens) FILTER (WHERE is_band_a)         AS band_a_tokens
    FROM mart_word_freq
),

milestones AS (
    SELECT UNNEST([50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1226]) AS top_n
)

SELECT
    m.top_n,
    r.cum_tokens,
    ROUND(100.0 * r.cum_tokens / t.all_tokens, 1)      AS pct_of_all_vocab,
    ROUND(100.0 * r.cum_tokens / t.band_a_tokens, 1)   AS pct_of_band_a_vocab
FROM milestones AS m
JOIN ranked AS r
    ON r.mvp_rank = m.top_n
CROSS JOIN totals AS t
ORDER BY m.top_n;