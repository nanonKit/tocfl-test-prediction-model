-- Staging · text segments

CREATE OR REPLACE TABLE stg_segments AS
SELECT
    source,
    set_id,
    section,
    part,
    q_no,
    seq,
    seg_type,
    NULLIF(option_label, '')   AS option_label,
    text
FROM read_csv(
    'data/interim/parsed/all_segments.csv',
    header = true,
    columns = {
        'source': 'VARCHAR', 'set_id': 'VARCHAR', 'section': 'VARCHAR', 'part': 'INTEGER',
        'q_no': 'INTEGER', 'seq': 'INTEGER', 'seg_type': 'VARCHAR', 'option_label': 'VARCHAR',
        'text': 'VARCHAR'
    }
);

CREATE OR REPLACE TABLE stg_booklet_segments AS
SELECT
    set_id,
    section,
    part,
    q_no,
    seq,
    seg_type,
    NULLIF(option_label, '')    AS option_label,
    NULLIF(text, '')            AS text,
    COALESCE(text, '') <> ''    AS has_text,     -- FALSE = picture (option) or picture/audio-only (stem)
    page
FROM read_csv(
    'data/interim/parsed/booklet_segments.csv',
    header = true,
    columns = {
        'set_id': 'VARCHAR', 'section': 'VARCHAR', 'part': 'INTEGER', 'q_no': 'INTEGER',
        'seq': 'INTEGER', 'seg_type': 'VARCHAR', 'option_label': 'VARCHAR', 'text': 'VARCHAR',
        'page': 'INTEGER'
    }
);