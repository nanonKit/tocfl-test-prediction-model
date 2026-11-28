-- one row per test question (5 sets x listening/reading x 50)

CREATE OR REPLACE TABLE dim_item AS
WITH part_names AS (
    SELECT * FROM (VALUES
        ('listening', 1, 'Picture Description'),
        ('listening', 2, 'Single-round Dialogue'),
        ('listening', 3, 'Multiple-round Dialogue'),
        ('listening', 4, 'Dialogue'),
        ('reading',   1, 'Sentence Comprehension'),
        ('reading',   2, 'Picture Description'),
        ('reading',   3, 'Gap Filling'),
        ('reading',   4, 'Paragraph Completion'),
        ('reading',   5, 'Reading Comprehension')
    ) AS t(section, part, part_name)
),

booklet_options AS (
    SELECT
        set_id, section, q_no,
        COUNT(*)                         AS n_options,
        BOOL_OR(has_text)                AS any_text_option
    FROM stg_booklet_segments
    WHERE seg_type = 'option'
    GROUP BY set_id, section, q_no
),

picture_text AS (                        -- Reading P2 pictures whose text was OCR'd
    SELECT DISTINCT set_id, section, q_no
    FROM stg_segments
    WHERE source = 'ocr'
),

tokens AS (
    SELECT
        item_id,
        COUNT(*)                  AS n_vocab_tokens,
        COUNT(DISTINCT entry_id)  AS n_entries
    FROM fact_item_token
    GROUP BY item_id
)

SELECT
    a.set_id || '_' || a.section || '_' || LPAD(CAST(a.q_no AS VARCHAR), 2, '0') AS item_id,
    a.set_id,
    a.section,
    a.part,
    p.part_name,
    a.q_no,
    a.answer,
    a.has_print_typo,
    CASE
        WHEN o.any_text_option                          THEN 'text'
        WHEN o.n_options > 0                            THEN 'picture'
        WHEN a.section = 'reading' AND a.part = 4       THEN 'text'      -- cloze blank: options sit on the passage
        ELSE 'audio'
    END                                   AS option_mode,
    pt.q_no IS NOT NULL                   AS has_picture_text,
    COALESCE(t.n_vocab_tokens, 0)         AS n_vocab_tokens,
    COALESCE(t.n_entries, 0)              AS n_entries
FROM stg_answer_keys AS a
LEFT JOIN part_names AS p
    ON p.section = a.section AND p.part = a.part
LEFT JOIN booklet_options AS o
    ON o.set_id = a.set_id AND o.section = a.section AND o.q_no = a.q_no
LEFT JOIN picture_text AS pt
    ON pt.set_id = a.set_id AND pt.section = a.section AND pt.q_no = a.q_no
LEFT JOIN tokens AS t
    ON t.item_id = a.set_id || '_' || a.section || '_' || LPAD(CAST(a.q_no AS VARCHAR), 2, '0');