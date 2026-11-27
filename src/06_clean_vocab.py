# Cleaning the official TOCFL 8000-word list.

import csv
import re
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path

import openpyxl
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "paths.yaml"

# English label inside the sheet name -> (level code, order). Band A = order <= 4.
LEVELS = {"Novice 1": ("N1", 1), "Novice 2": ("N2", 2), "Level 1": ("L1", 3), "Level 2": ("L2", 4),
          "Level 3": ("L3", 5), "Level 4": ("L4", 6), "Level 5": ("L5", 7)}
SUMMARY_SHEET = "各等詞條數(Entry Number)"            # official entry count per level, used to validate
RE_SHEET_LEVEL = re.compile(r"\((Novice \d|Level \d)\)")
RE_ZHUYIN_HINT = re.compile(r"[（(][\u3105-\u312F˙ˊˇˋ\uf8f8\s]+[)）]")   # (˙ㄗ) (ㄓㄠ) — pronunciation notes
RE_OPTIONAL = re.compile(r"[（(]([\u4e00-\u9fff]+)\s*[)）]")             # (子) — optional characters
BREVE_TO_CARON = str.maketrans("ăĕĭŏŭĂĔĬŎŬ", "ǎěǐǒǔǍĚǏǑǓ")              # 3rd tone is a caron, not a breve


@dataclass
class Entry:
    entry_id: int
    level: str
    level_order: int
    topic: str             # 任務領域 — only Novice 1 to Level 2 have it
    raw_vocab: str         # as printed, for audit
    pinyin: str
    pos: str               # may hold several, e.g. "N/V"


@dataclass
class Form:
    entry_id: int
    form: str


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def expand_forms(raw: str) -> list[str]:
    """'窗(子)/窗戶(˙ㄏㄨ)' -> ['窗', '窗子', '窗戶']  (order kept, duplicates removed)."""
    forms: list[str] = []
    for variant in RE_ZHUYIN_HINT.sub("", raw).split("/"):
        variant = re.sub(r"\s+", "", variant)
        parts = RE_OPTIONAL.split(variant)               # odd positions are the optional pieces
        choices = [[p] if i % 2 == 0 else ["", p] for i, p in enumerate(parts)]
        for combo in product(*choices):
            form = "".join(combo)
            if form and form not in forms:
                forms.append(form)
    return forms


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip() if value is not None else ""


def read_levels(xlsx: Path) -> tuple[list[Entry], list[Form], dict[str, int]]:
    entries: list[Entry] = []
    forms: list[Form] = []
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    try:
        for sheet in wb.worksheets:
            m = RE_SHEET_LEVEL.search(sheet.title)
            if not m:
                continue                                  # summary / comparison sheets
            level, order = LEVELS[m.group(1)]
            rows = sheet.iter_rows(min_row=2, values_only=True)
            for row in rows:
                if len(row) == 4:                         # Novice 1 - Level 2: topic, word, pinyin, POS
                    topic, vocab, pinyin, pos = row
                else:                                     # Level 3 - 5 have no topic column
                    topic, (vocab, pinyin, pos) = None, row
                if vocab is None:
                    continue                              # trailing empty rows
                entry_id = len(entries) + 1
                entries.append(Entry(entry_id, level, order, clean_text(topic), clean_text(vocab),
                                     clean_text(pinyin).translate(BREVE_TO_CARON),
                                     re.sub(r"\s*/\s*", "/", clean_text(pos))))
                forms.extend(Form(entry_id, f) for f in expand_forms(str(vocab)))
        official = read_official_counts(wb[SUMMARY_SHEET])
    finally:
        wb.close()
    return entries, forms, official


def read_official_counts(sheet) -> dict[str, int]:
    """Row 2 of the summary sheet = entries per level, in level order."""
    counts = next(sheet.iter_rows(min_row=2, max_row=2, values_only=True))[1:8]
    return {code: int(n) for (code, _), n in zip(LEVELS.values(), counts)}


def validate(entries: list[Entry], forms: list[Form], official: dict[str, int]) -> None:
    for level, expected in official.items():
        got = sum(e.level == level for e in entries)
        if got != expected:
            raise ValueError(f"{level}: {got} entries, official summary says {expected}")
    without_form = {e.entry_id for e in entries} - {f.entry_id for f in forms}
    if without_form:
        raise ValueError(f"{len(without_form)} entries produced no written form, e.g. id {min(without_form)}")
    leftovers = [f.form for f in forms if not re.fullmatch(r"[\u4e00-\u9fff]+", f.form)]
    if leftovers:
        raise ValueError(f"{len(leftovers)} forms still contain non-Chinese characters: {leftovers[:10]}")


def write_csv(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(r) for r in rows)


def main() -> None:
    cfg = load_config()
    out_dir = ROOT / cfg["interim_dir"] / "parsed"
    entries, forms, official = read_levels(Path(cfg["vocab_xlsx"]))
    validate(entries, forms, official)

    print(f"{'level':<7}{'entries':>8}{'forms':>7}{'official':>10}")
    for level, _ in LEVELS.values():
        ids = {e.entry_id for e in entries if e.level == level}
        print(f"{level:<7}{len(ids):>8}{sum(f.entry_id in ids for f in forms):>7}{official[level]:>10}")

    write_csv(out_dir / "vocab_entries.csv", entries)
    write_csv(out_dir / "vocab_forms.csv", forms)
    band_a = sum(e.level_order <= 4 for e in entries)
    print(f"\nDone: {len(entries)} entries ({band_a} in Band A), {len(forms)} forms -> {out_dir}")


if __name__ == "__main__":
    main()