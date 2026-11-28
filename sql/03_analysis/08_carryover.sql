-- if a word appeared in k of the other 4 sets, how likely is it in the held-out set?

CREATE OR REPLACE TEMP VIEW v_carryover AS
WITH sets AS (
    SELECT DISTINCT set_id FROM fact_item_token
),

word_in_set AS (                               -- 1 row per (word, set) where it appears
    SELECT DISTINCT entry_id, set_id
    FROM fact_item_token
),

grid AS (                                      -- every Band A word x every held-out set
    SELECT m.entry_id, m.level, m.level_order, s.set_id AS held_out
    FROM mart_word_freq AS m
    CROSS JOIN sets AS s
    WHERE m.is_band_a
)

SELECT
    g.entry_id,
    g.level,
    g.level_order,
    g.held_out,
    (SELECT COUNT(*) FROM word_in_set AS w
     WHERE w.entry_id = g.entry_id AND w.set_id <> g.held_out)          AS k_other_sets,
    EXISTS (SELECT 1 FROM word_in_set AS w
            WHERE w.entry_id = g.entry_id AND w.set_id = g.held_out)    AS in_held_out
FROM grid AS g;

-- 1) the more past sets a word was in, the more likely it shows up in the new one?
SELECT
    k_other_sets,
    COUNT(*)                                                         AS word_set_pairs,
    COUNT(*) FILTER (WHERE in_held_out)                              AS appeared,
    ROUND(100.0 * COUNT(*) FILTER (WHERE in_held_out) / COUNT(*), 1) AS pct_appears_in_held_out
FROM v_carryover
GROUP BY k_other_sets
ORDER BY k_other_sets;

-- 2) never-seen words (k = 0): does their level change the odds?
SELECT
    level,
    COUNT(*)                                                         AS word_set_pairs,
    ROUND(100.0 * COUNT(*) FILTER (WHERE in_held_out) / COUNT(*), 1) AS pct_appears_in_held_out
FROM v_carryover
WHERE k_other_sets = 0
GROUP BY level
ORDER BY MIN(level_order);