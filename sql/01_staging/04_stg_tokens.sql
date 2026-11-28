-- Staging · CKIP tokens

CREATE OR REPLACE TABLE stg_tokens AS
SELECT
    source,
    set_id,
    section,
    part,
    q_no,
    seq,
    token_idx,
    token,
    pos,
    CASE
        WHEN pos LIKE '%CATEGORY' THEN 'punct'     -- CKIP punctuation tags: PERIODCATEGORY, COMMACATEGORY ...
        WHEN pos = 'Nb'           THEN 'name'      -- proper noun: 王小明, 台北
        WHEN pos = 'Neu'          THEN 'number'    -- numerals: 三, 2016
        WHEN pos = 'FW'           THEN 'foreign'   -- Latin letters, e-mail, codes
        ELSE 'word'
    END AS token_class
FROM read_csv(
    'data/interim/parsed/tokens.csv',
    header = true,
    columns = {
        'source': 'VARCHAR', 'set_id': 'VARCHAR', 'section': 'VARCHAR', 'part': 'INTEGER',
        'q_no': 'INTEGER', 'seq': 'INTEGER', 'token_idx': 'INTEGER', 'token': 'VARCHAR',
        'pos': 'VARCHAR'
    }
);