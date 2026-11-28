-- Staging · official answer keys

CREATE OR REPLACE TABLE stg_answer_keys AS
SELECT
    set_id,
    section,
    part,
    q_no,
    printed_q_no,
    answer,
    q_no <> printed_q_no   AS has_print_typo   -- official key prints the wrong number (q34 -> 44)
FROM read_csv(
    'data/interim/parsed/answer_keys.csv',
    header = true,
    columns = {
        'set_id': 'VARCHAR', 'section': 'VARCHAR', 'part': 'INTEGER', 'q_no': 'INTEGER',
        'printed_q_no': 'INTEGER', 'answer': 'VARCHAR'
    }
);