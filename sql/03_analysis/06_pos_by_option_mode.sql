-- part of speech of the vocabulary, picture items vs text items

WITH token_pos AS (
    SELECT
        i.option_mode,
        CASE
            WHEN SPLIT_PART(w.pos, '/', 1) = 'N'         THEN 'noun'
            WHEN SPLIT_PART(w.pos, '/', 1) LIKE 'V%'     THEN 'verb / adjective'   -- TOCFL: Vs = state verb ≈ adjective
            WHEN SPLIT_PART(w.pos, '/', 1) = 'M'         THEN 'measure word'
            WHEN SPLIT_PART(w.pos, '/', 1) = 'Adv'       THEN 'adverb'
            ELSE 'function word'                                                -- Det, Ptc, Conj, Prep, ...
        END AS word_class
    FROM fact_item_token AS f
    JOIN dim_word AS w
        ON w.entry_id = f.entry_id
    JOIN dim_item AS i
        ON i.item_id = f.item_id
)

SELECT
    word_class,
    ROUND(100.0 * COUNT(*) FILTER (WHERE option_mode = 'picture')
          / SUM(COUNT(*) FILTER (WHERE option_mode = 'picture')) OVER (), 1) AS pct_in_picture_items,
    ROUND(100.0 * COUNT(*) FILTER (WHERE option_mode = 'text')
          / SUM(COUNT(*) FILTER (WHERE option_mode = 'text')) OVER (), 1)    AS pct_in_text_items,
    ROUND(100.0 * COUNT(*) FILTER (WHERE option_mode = 'audio')
          / SUM(COUNT(*) FILTER (WHERE option_mode = 'audio')) OVER (), 1)   AS pct_in_audio_items
FROM token_pos
GROUP BY word_class
ORDER BY pct_in_picture_items DESC;