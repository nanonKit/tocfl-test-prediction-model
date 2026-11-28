-- Staging · official TOCFL word list

CREATE OR REPLACE TABLE stg_vocab_entries AS
SELECT
    entry_id,
    level,
    level_order,
    NULLIF(topic, '')   AS topic,          -- only Novice 1 - Level 2 carry a topic
    raw_vocab,
    pinyin,
    NULLIF(pos, '')     AS pos,
    level_order <= 4    AS is_band_a       -- N1, N2, L1, L2 = Band A scope
FROM read_csv(
    'data/interim/parsed/vocab_entries.csv',
    header = true,
    columns = {
        'entry_id': 'INTEGER', 'level': 'VARCHAR', 'level_order': 'INTEGER', 'topic': 'VARCHAR',
        'raw_vocab': 'VARCHAR', 'pinyin': 'VARCHAR', 'pos': 'VARCHAR'
    }
);

CREATE OR REPLACE TABLE stg_vocab_forms AS
SELECT
    entry_id,
    form
FROM read_csv(
    'data/interim/parsed/vocab_forms.csv',
    header = true,
    columns = {'entry_id': 'INTEGER', 'form': 'VARCHAR'}
);