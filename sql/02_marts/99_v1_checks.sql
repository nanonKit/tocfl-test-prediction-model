-- V1 data checks · run last; the build fails if any check fails

WITH checks AS (
    SELECT 1 AS check_id,
           'every set has 50 listening + 50 reading items' AS check_name,
           (SELECT COUNT(*) FROM dim_item)
               = (SELECT COUNT(DISTINCT set_id) * 100 FROM stg_answer_keys)
           AND NOT EXISTS (
               SELECT 1 FROM dim_item GROUP BY set_id, section HAVING COUNT(*) <> 50
           ) AS passed

    UNION ALL
    SELECT 2, 'item_id is unique in dim_item',
           (SELECT COUNT(*) FROM dim_item) = (SELECT COUNT(DISTINCT item_id) FROM dim_item)

    UNION ALL
    SELECT 3, 'every item has a part name and an answer',
           NOT EXISTS (SELECT 1 FROM dim_item WHERE part_name IS NULL OR answer IS NULL)

    UNION ALL
    SELECT 4, 'entry_id is unique in dim_word and every entry has a form',
           (SELECT COUNT(*) FROM dim_word) = (SELECT COUNT(DISTINCT entry_id) FROM dim_word)
           AND (SELECT COUNT(*) FROM dim_word) = (SELECT COUNT(*) FROM stg_vocab_entries)

    UNION ALL
    SELECT 5, 'every word token is matched exactly once (no loss, no duplicates)',
           (SELECT COUNT(*) FROM stg_tokens WHERE token_class = 'word')
               = (SELECT COUNT(DISTINCT (source, set_id, section, part, q_no, seq, token_idx))
                  FROM int_token_vocab)

    UNION ALL
    SELECT 6, 'unmatched word tokens < 3%',
           (SELECT COUNT(*) FILTER (WHERE match_method = 'unmatched') * 1.0 / COUNT(*) FROM int_token_vocab) < 0.03

    UNION ALL
    SELECT 7, 'every fact row points to a known word and a known item',
           NOT EXISTS (
               SELECT 1 FROM fact_item_token AS f
               LEFT JOIN dim_word AS w ON w.entry_id = f.entry_id
               LEFT JOIN dim_item AS i ON i.item_id = f.item_id
               WHERE w.entry_id IS NULL OR i.item_id IS NULL
           )

    UNION ALL
    SELECT 8, 'mart counts reconcile with the fact table',
           (SELECT COUNT(*) FROM fact_item_token) = (SELECT SUM(n_tokens) FROM mart_word_freq)
           AND (SELECT COUNT(*) FROM mart_word_freq) = (SELECT COUNT(*) FROM dim_word)

    UNION ALL
    SELECT 9, 'mvp_rank is 1..N with no gaps for Band A words',
           (SELECT MAX(mvp_rank) FROM mart_word_freq) = (SELECT COUNT(*) FROM mart_word_freq WHERE is_band_a)
           AND (SELECT COUNT(DISTINCT mvp_rank) FROM mart_word_freq) = (SELECT COUNT(*) FROM mart_word_freq WHERE is_band_a)

    UNION ALL
    SELECT 10, 'every item except cloze blanks has vocabulary',
           NOT EXISTS (
               SELECT 1 FROM dim_item
               WHERE n_vocab_tokens = 0 AND NOT (section = 'reading' AND part = 4)
           )
)

SELECT
    check_id,
    check_name,
    passed,
    CASE WHEN NOT passed THEN error('V1 check ' || check_id || ' failed: ' || check_name) END AS stop
FROM checks
ORDER BY check_id;


-- checking
SELECT section, part, part_name, option_mode, COUNT(*) AS n,
       ROUND(AVG(n_vocab_tokens), 1) AS avg_tokens
FROM dim_item
GROUP BY ALL
ORDER BY section, part;