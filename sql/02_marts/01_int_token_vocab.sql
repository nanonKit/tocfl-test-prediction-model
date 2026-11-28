-- map every word token to the official vocabulary

CREATE OR REPLACE TABLE int_token_vocab AS
WITH form_entry AS (                      -- one entry per written form: the most basic level
    SELECT
        f.form,
        e.entry_id
    FROM stg_vocab_forms AS f
    JOIN stg_vocab_entries AS e
        ON e.entry_id = f.entry_id
    QUALIFY ROW_NUMBER() OVER (PARTITION BY f.form ORDER BY e.level_order, e.entry_id) = 1
),

words AS (
    SELECT source, set_id, section, part, q_no, seq, token_idx, token
    FROM stg_tokens
    WHERE token_class = 'word'
),


-- token is an official written form
exact AS (
    SELECT
        w.*,
        1           AS part_idx,
        fe.form,
        fe.entry_id,
        'exact'     AS match_method
    FROM words AS w
    JOIN form_entry AS fe
        ON fe.form = w.token
),

split_cuts AS (                           -- every cut position of tokens with no exact match
    SELECT
        w.*,
        UNNEST(RANGE(1, LENGTH(w.token))) AS cut
    FROM words AS w
    WHERE NOT EXISTS (SELECT 1 FROM form_entry AS fe WHERE fe.form = w.token)
),


-- token = form + form. CKIP keeps some compounds whole that  很多 -> 很 + 多
-- the list stores as two words; if several cuts work, the    火車站 -> 火車 + 站
-- longest first part wins
split2 AS (                               -- keep the cut whose two halves are both official forms
    SELECT
        c.*,
        lf.form      AS left_form,
        lf.entry_id  AS left_entry_id,
        rf.form      AS right_form,
        rf.entry_id  AS right_entry_id
    FROM split_cuts AS c
    JOIN form_entry AS lf
        ON lf.form = LEFT(c.token, c.cut)
    JOIN form_entry AS rf
        ON rf.form = SUBSTR(c.token, c.cut + 1)
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY c.source, c.set_id, c.section, c.part, c.q_no, c.seq, c.token_idx
        ORDER BY c.cut DESC
    ) = 1
),

split_parts AS (                          -- one row per half
    SELECT source, set_id, section, part, q_no, seq, token_idx, token,
           1 AS part_idx, left_form AS form, left_entry_id AS entry_id, 'split2' AS match_method
    FROM split2
    UNION ALL
    SELECT source, set_id, section, part, q_no, seq, token_idx, token,
           2 AS part_idx, right_form AS form, right_entry_id AS entry_id, 'split2' AS match_method
    FROM split2
),

unmatched AS (
    SELECT
        w.*,
        1                     AS part_idx,
        CAST(NULL AS VARCHAR) AS form,
        CAST(NULL AS INTEGER) AS entry_id,
        'unmatched'           AS match_method
    FROM words AS w
    WHERE NOT EXISTS (SELECT 1 FROM form_entry AS fe WHERE fe.form = w.token)
      AND NOT EXISTS (
          SELECT 1 FROM split2 AS s
          WHERE (s.source, s.set_id, s.section, s.part, s.q_no, s.seq, s.token_idx)
              = (w.source, w.set_id, w.section, w.part, w.q_no, w.seq, w.token_idx)
      )
)

SELECT source, set_id, section, part, q_no, seq, token_idx, token, part_idx, form, entry_id, match_method
FROM exact
UNION ALL
SELECT source, set_id, section, part, q_no, seq, token_idx, token, part_idx, form, entry_id, match_method
FROM split_parts
UNION ALL
SELECT source, set_id, section, part, q_no, seq, token_idx, token, part_idx, form, entry_id, match_method
FROM unmatched;


SELECT
    match_method,
    COUNT(DISTINCT (source, set_id, section, part, q_no, seq, token_idx)) AS tokens,
    ROUND(100.0 * tokens / 14088, 1)                                       AS pct
FROM int_token_vocab
GROUP BY match_method
ORDER BY tokens DESC;