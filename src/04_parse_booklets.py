
# Parse test booklest (reading + listening) into text segments and answer keys

import csv
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "paths.yaml"

SECTION_BY_PREFIX = {"ls": "listening", "rd": "reading"}
PART_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
RE_PAGE = re.compile(r"^=== page (\d+) ===$")
RE_PART = re.compile(r"^第([一二三四五])部分")
RE_THAI = re.compile(r"[\u0E00-\u0E7F]")                                    # Thai instruction lines are dropped
RE_QNUM = re.compile(r"^(\d{1,2})[.．]\s*(.*)$")                            # "31. 冬天快到了…" or "16."
RE_OPTION_START = re.compile(r"^[（(][A-F][)）]")                           # (A) or （A）
RE_OPTION_SPLIT = re.compile(r"[（(]([A-F])[)）]")                          # several options may share one line
RE_PASSAGE_MARK = re.compile(r"^[（(][一二三四五六七八九十]+[)）]$")          # (一) starts a reading passage
RE_BLANK = re.compile(r"[（(]\s*(\d{1,2})\s*[)）]")                         # （41） blank inside a passage
EXAMPLE_END = "答案卡"                                                      # "…請把答案塗在答案卡上。" closes the worked example
TEST_END = "全部結束"                                                       # "聽力考試到這裡全部結束。" footer
SUMMARY_COLUMNS = [("stem", True), ("stem", False), ("option", True), ("option", False), ("passage", None)]


@dataclass
class Segment:
    set_id: str
    section: str
    part: int
    q_no: int | None
    seq: int
    seg_type: str            # stem | option | passage
    option_label: str        # A-F for options, "" otherwise
    text: str                # "" = picture (option) or picture/audio-only (stem)
    page: int


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean_lines(raw: str) -> list[str]:
    lines = (line.strip().replace("\u3000", "") for line in raw.splitlines())
    return [line for line in lines if line and not RE_THAI.search(line)]


def parse_booklet(set_id: str, section: str, raw: str) -> list[Segment]:
    """State machine. Each part opens with instructions + a worked example: skip them
    until the first page break after the example's answer line."""
    segments: list[Segment] = []
    part = page = 0
    q_no: int | None = None
    current: Segment | None = None
    in_example = example_done = False

    def open_segment(seg_type: str, label: str = "", text: str = "") -> None:
        nonlocal current
        current = Segment(set_id, section, part, q_no, 0, seg_type, label, text.strip(), page)
        segments.append(current)

    for line in clean_lines(raw):
        if m := RE_PAGE.match(line):
            page = int(m.group(1))
            if example_done:
                in_example = example_done = False
        elif m := RE_PART.match(line):
            part, q_no, current = PART_NUM[m.group(1)], None, None
            in_example, example_done = True, False
        elif in_example or TEST_END in line:
            example_done = example_done or (in_example and EXAMPLE_END in line)
        elif RE_PASSAGE_MARK.match(line):
            q_no = None
            open_segment("passage")
        elif m := RE_QNUM.match(line):
            q_no = int(m.group(1))
            open_segment("stem", text=m.group(2))                       # "" = picture/audio-only stem
        elif RE_OPTION_START.match(line):
            pieces = RE_OPTION_SPLIT.split(line)[1:]                    # ['A', 'text', 'B', 'text', …]
            for label, text in zip(pieces[::2], pieces[1::2]):
                open_segment("option", label=label, text=text)
        elif current is None or (current.seg_type == "option" and RE_BLANK.search(line)):
            open_segment("passage", text=line)                          # unnumbered text with blanks: cloze passage
        else:
            current.text += line

    fill_group_q_no(segments)
    for i, seg in enumerate(segments):                   # seq = order inside (part, q_no)
        seg.seq = sum(1 for s in segments[:i] if (s.part, s.q_no) == (seg.part, seg.q_no)) + 1
    return segments


def fill_group_q_no(segments: list[Segment]) -> None:
    """Passages (and Part-4 shared options) have no number of their own.
    Cloze passage -> its first blank; other passage -> the next question; options -> their passage."""
    for i, seg in enumerate(segments):
        if seg.q_no is not None:
            continue
        if seg.seg_type == "passage":
            blanks = [int(b) for b in RE_BLANK.findall(seg.text)]
            following = next((s.q_no for s in segments[i + 1:] if s.q_no is not None and s.part == seg.part), None)
            seg.q_no = min(blanks) if blanks else following
        else:
            seg.q_no = segments[i - 1].q_no


def questions_covered(segments: list[Segment]) -> dict[int, set[int]]:
    """Question numbers that appear in the booklet, per part (numbered lines + cloze blanks)."""
    covered: dict[int, set[int]] = defaultdict(set)
    for s in segments:
        covered[s.part].add(s.q_no)
        covered[s.part].update(int(b) for b in RE_BLANK.findall(s.text))
    return covered


def load_answer_parts(path: Path) -> dict[tuple[str, str, int], set[int]]:
    parts: dict[tuple[str, str, int], set[int]] = defaultdict(set)
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            parts[(row["set_id"], row["section"], int(row["part"]))].add(int(row["q_no"]))
    return parts


def validate(set_id: str, section: str, segments: list[Segment], answer_parts: dict) -> None:
    """V1: every question in the answer key must appear in the same part of the booklet."""
    covered = questions_covered(segments)
    for (s_id, sec, part), expected in answer_parts.items():
        if (s_id, sec) != (set_id, section):
            continue
        missing = expected - covered.get(part, set())
        if missing:
            raise ValueError(f"{set_id} {section} part {part}: missing q {sorted(missing)}")


def count_segments(segments: list[Segment], seg_type: str, has_text: bool | None) -> int:
    return sum(s.seg_type == seg_type and (has_text is None or bool(s.text) == has_text) for s in segments)


def main() -> None:
    cfg = load_config()
    interim = ROOT / cfg["interim_dir"]
    out_path = interim / "parsed" / "booklet_segments.csv"
    answer_parts = load_answer_parts(interim / "parsed" / "answer_keys.csv")

    files = sorted((interim / "text").glob("mock*/*_tha_t.txt"))
    if not files:
        raise FileNotFoundError("No booklets found — run 01_extract_text.py first")

    all_segments: list[Segment] = []
    print(f"{'set':<7}{'section':<11}" + "".join(f"{h:>9}" for h in ("stem", "img_stem", "option", "img_opt", "passage")))
    for path in files:
        set_id, section = path.parent.name, SECTION_BY_PREFIX[path.name[:2]]
        segments = parse_booklet(set_id, section, path.read_text(encoding="utf-8"))
        validate(set_id, section, segments, answer_parts)
        all_segments.extend(segments)

        counts = [count_segments(segments, t, has_text) for t, has_text in SUMMARY_COLUMNS]
        print(f"{set_id:<7}{section:<11}" + "".join(f"{n:>9}" for n in counts))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(all_segments[0])))
        writer.writeheader()
        writer.writerows(asdict(s) for s in all_segments)

    print(f"\nDone: {len(all_segments)} segments -> {out_path}")


if __name__ == "__main__":
    main()