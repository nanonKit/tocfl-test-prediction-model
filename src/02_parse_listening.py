# Parse listening text into text segments

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]                   # finding repo root src/... >> not crash when change the directory
CONFIG_PATH = ROOT / "config" / "paths.yaml"  
EXPECTED_ITEMS = 50                                          # listening items per set

PART_NUM = {"一": 1, "二": 2, "三": 3, "四": 4}
RE_PAGE = re.compile(r"^=== page (\d+) ===$")
RE_PART = re.compile(r"^第([一二三四])部分")
RE_QNUM = re.compile(r"^(\d{1,2})\.$")                                  # "12." alone on its line
RE_OPTION = re.compile(r"^\(([A-D])\)\s*(.*)$")                         # "(A)" or "(A) 銀行"
RE_SPEAKER = re.compile(r"^([男女]\d?)(?:$|\s*[：:]|\s)\s*(.*)$")       # 男 / 男：你好 / 女1 妳們… — not 女孩怎麼了？
SKIP_LINES = {"提問", "Script of Listening Test"}
RE_TITLE = re.compile(r"^入門基礎級.*(文本|腳本)$")

@dataclass
class Segment:
    set_id: str
    part: int
    q_no: int
    seq: int                    # order of the segment inside its question
    seg_type: str               # stem | option | utterance
    option_label: str           # A-D for option, "" otherwise
    speaker: str                # 男 / 女 / 女1 for utterances, "" otherwise
    text: str
    page: int      


def load_config(path: Path = CONFIG_PATH) -> dict:          # reading yaml path >> even through adjusted folder name, just edit only yaml file, not the code
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean_lines(raw: str) -> list[str]:          # clean text lines from pdf
    """Split whitespace (incl. full-width space) and drop empty lines."""
    lines = (line.strip() .replace("\u3000", "") for line in raw.splitlines())
    return [line for line in lines if line]


def parse_script(set_id: str, raw: str) -> list[Segment]:          # parse listening script into segments
    """Line-based state machine:; markers open a new segment, other lines continue it"""
    segments: list[Segment] = []
    part = q_no = page = 0
    current: Segment | None = None


    def open_segment(seg_type: str, label: str = "", speaker: str = "", text: str = "") -> None:
        nonlocal current
        seq = sum(1 for s in segments if s.q_no == q_no) + 1
        current = Segment(set_id, part, q_no, seq, seg_type, label, speaker, text, page)
        segments.append(current)


    for line in clean_lines(raw):
        if m := RE_PAGE.match(line):
            page = int(m.group(1))
        elif line in SKIP_LINES or RE_TITLE.match(line):
            continue
        elif m := RE_PART.match(line):
            part, current = PART_NUM[m.group(1)], None
        elif m := RE_QNUM.match(line):
            q_no, current = int(m.group(1)), None
        elif m := RE_OPTION.match(line):
            open_segment("option", label=m.group(1), text=m.group(2))
        elif m := RE_SPEAKER.match(line):
            open_segment("utterance", speaker=m.group(1), text=m.group(2))
        elif current is None:
            open_segment("stem", text=line)             # first free text after "12." = question stem
        else:
            current.text += line                        # wrapped line: Chinese needs no space

    return segments


def validate(set_id: str, segments: list[Segment]) -> None:          # validate the parsed segments
    """Fail loudly if a set does not have questions 1-50 with text"""
    q_nos = sorted({s.q_no for s in segments})
    if q_nos != list(range(1, EXPECTED_ITEMS + 1)):
        missing = set(range(1, EXPECTED_ITEMS + 1)) - set(q_nos)
        raise ValueError(f"{set_id}: expected q 1-{EXPECTED_ITEMS}, missing {sorted(missing)}")
    empty = [s for s in segments if not s.text]
    if empty:
        raise ValueError(f"{set_id}: {len(empty)} empty segments, first = {empty[0]}")


def main() -> None:
    cfg = load_config()
    text_dir = ROOT / cfg["interim_dir"] / "text"
    out_path = ROOT / cfg["interim_dir"] / "parsed" / "listening_segments.csv"

    files = sorted(text_dir.glob("mock*/ls_*_listen.txt"))
    if not files:
        raise FileNotFoundError(f"No listening scripts under {text_dir} - run 01_extract_text.py first")

    all_segments: list[Segment] = []
    print(f"{'set':<7}{'q':>4}{'p1':>5}{'p2':>5}{'p3':>5}{'p4':>5}{'segments':>10}")
    for path in files:
        set_id = path.parent.name
        segments = parse_script(set_id, path.read_text(encoding="utf-8"))
        validate(set_id, segments)
        all_segments.extend(segments)

        q_per_part = [len({s.q_no for s in segments if s.part == p}) for p in (1, 2, 3, 4)]
        print(f"{set_id:<7}{len({s.q_no for s in segments}):>4}"
              + "".join(f"{n:>5}" for n in q_per_part) +  f"{len(segments):>10}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:            # -sig: Excel shows Chinese correctly
        writer = csv.DictWriter(f, fieldnames=list(asdict(all_segments[0])))
        writer.writeheader()
        writer.writerows(asdict(s) for s in all_segments)

    print(f"\nDone: {len(all_segments)} segments -> {out_path}")


if __name__ == "__main__":
    main()