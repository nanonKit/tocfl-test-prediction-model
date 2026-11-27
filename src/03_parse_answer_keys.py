# Parse official answer keys (listening and reading)

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "paths.yaml"
EXPECTED_ITEMS = 50                                                 # per section per set

SECTION_BY_PREFIX = {"ls": "listening", "rd": "reading"}
PART_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
RE_PART_ZH = re.compile(r"^第([一二三四五])部分")                    # 第二部分 問答理解
RE_PART_EN = re.compile(r"^Part (\d)")                              # Part 2 ... (mock04 has English headers only)
RE_NUMBER = re.compile(r"^(\d{1,2})$")
RE_ANSWER = re.compile(r"^([A-F])$")                                # A-C / A-D, A-F for paragraph completion


@dataclass
class AnswerKey:
    set_id: str
    section: str
    part: int
    q_no: int              # position in the key (1..50) = the true question number
    printed_q_no: int      # number as printed — differs only where the official key has a typo
    answer: str


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_key(set_id: str, section: str, raw: str) -> list[AnswerKey]:
    """Pair each number line with the answer letter that follows it."""
    keys: list[AnswerKey] = []
    part = 0
    printed: int | None = None

    for line in (ln.strip() for ln in raw.splitlines()):
        if m := RE_PART_ZH.match(line):
            part = PART_NUM[m.group(1)]
        elif m := RE_PART_EN.match(line):
            part = int(m.group(1))
        elif m := RE_NUMBER.match(line):
            printed = int(m.group(1))
        elif (m := RE_ANSWER.match(line)) and printed is not None:
            # Keys list questions strictly in order, so position is more reliable than the printed number
            keys.append(AnswerKey(set_id, section, part, len(keys) + 1, printed, m.group(1)))
            printed = None

    return keys


def validate(set_id: str, section: str, keys: list[AnswerKey]) -> None:
    if len(keys) != EXPECTED_ITEMS:
        raise ValueError(f"{set_id} {section}: expected {EXPECTED_ITEMS} answers, got {len(keys)}")
    if any(k.part == 0 for k in keys):
        raise ValueError(f"{set_id} {section}: answers found before any part header")


def main() -> None:
    cfg = load_config()
    text_dir = ROOT / cfg["interim_dir"] / "text"
    out_path = ROOT / cfg["interim_dir"] / "parsed" / "answer_keys.csv"

    files = sorted(text_dir.glob("mock*/*_answer.txt"))
    if not files:
        raise FileNotFoundError(f"No answer keys under {text_dir} — run 01_extract_text.py first")

    all_keys: list[AnswerKey] = []
    print(f"{'set':<7}{'section':<11}{'n':>4}  {'items per part':<20}typos")
    for path in files:
        set_id = path.parent.name
        section = SECTION_BY_PREFIX[path.name[:2]]
        keys = parse_key(set_id, section, path.read_text(encoding="utf-8"))
        validate(set_id, section, keys)
        all_keys.extend(keys)

        parts = sorted({k.part for k in keys})
        per_part = "/".join(str(sum(k.part == p for k in keys)) for p in parts)
        typos = [f"q{k.q_no} printed as {k.printed_q_no}" for k in keys if k.q_no != k.printed_q_no]
        print(f"{set_id:<7}{section:<11}{len(keys):>4}  {per_part:<20}{', '.join(typos) or '-'}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(all_keys[0])))
        writer.writeheader()
        writer.writerows(asdict(k) for k in all_keys)

    print(f"\nDone: {len(all_keys)} answers -> {out_path}")


if __name__ == "__main__":
    main()