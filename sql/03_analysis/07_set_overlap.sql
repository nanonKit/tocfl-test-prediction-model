-- how similar is the Band A vocabulary of two mock sets? (Jaccard overlap)

WITH set_words AS (
    SELECT DISTINCT
        f.set_id,
        f.entry_id
    FROM fact_item_token AS f
    JOIN dim_word AS w
        ON w.entry_id = f.entry_id
    WHERE w.is_band_a
),

set_size AS (
    SELECT set_id, COUNT(*) AS n_words
    FROM set_words
    GROUP BY set_id
),

shared AS (
    SELECT
        a.set_id AS set_a,
        b.set_id AS set_b,
        COUNT(*) AS n_shared
    FROM set_words AS a
    JOIN set_words AS b
        ON  b.entry_id = a.entry_id
        AND b.set_id > a.set_id                  -- each pair once, no self-pairs
    GROUP BY a.set_id, b.set_id
)

SELECT
    s.set_a,
    s.set_b,
    sa.n_words                                                AS words_a,
    sb.n_words                                                AS words_b,
    s.n_shared,
    ROUND(s.n_shared * 1.0 / (sa.n_words + sb.n_words - s.n_shared), 3) AS jaccard
FROM shared AS s
JOIN set_size AS sa ON sa.set_id = s.set_a
JOIN set_size AS sb ON sb.set_id = s.set_b
ORDER BY s.set_a, s.set_b;