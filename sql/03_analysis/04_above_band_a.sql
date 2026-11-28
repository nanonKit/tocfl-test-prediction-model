-- words above Band A (Level 3+) that still appear in the mock tests

WITH parts_seen AS (
    SELECT
        entry_id,
        STRING_AGG(DISTINCT section || ' P' || part, ', ' ORDER BY section || ' P' || part) AS seen_in
    FROM fact_item_token
    GROUP BY entry_id
)

SELECT
    m.headword,
    m.pinyin,
    m.level,
    m.pos,
    m.n_sets,
    m.n_tokens,
    p.seen_in
FROM mart_word_freq AS m
JOIN parts_seen AS p
    ON p.entry_id = m.entry_id
WHERE NOT m.is_band_a
  AND m.n_sets >= 2
ORDER BY m.n_sets DESC, m.n_tokens DESC, m.level_order;