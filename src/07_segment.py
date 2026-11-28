# Word segmentation + POS tagging with CKIP Transformers.

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
from ckip_transformers.nlp import CkipPosTagger, CkipWordSegmenter

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "paths.yaml"
CORRECTIONS_PATH = ROOT / "data" / "manual" / "ocr_corrections.csv"
CKIP_MODEL = "bert-base"                 # most accurate CKIP model; CPU is fine for ~40k characters
OCR_SECTION, OCR_PART, OCR_MIN_ZH = "reading", 2, 5   # pictures with real text (see 05_ocr_images.py)
PICTURE_KEY = ("set_id", "section", "page", "img_idx")


@dataclass
class TextSegment:
    source: str              # script | booklet | ocr
    set_id: str
    section: str
    part: int
    q_no: int
    seq: int                 # segment order inside its question (ocr: picture index on the page)
    seg_type: str            # stem | option | utterance | passage | picture
    option_label: str
    text: str


@dataclass
class Token:
    source: str
    set_id: str
    section: str
    part: int
    q_no: int
    seq: int
    token_idx: int
    token: str
    pos: str                 # CKIP tag, e.g. Na, VC, Nb (proper noun), PERIODCATEGORY


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def collect_segments(parsed: Path) -> list[TextSegment]:
    """Union the three text sources into one schema. Empty texts (pictures / audio only) are dropped."""
    segments = [
        TextSegment("script", r["set_id"], "listening", int(r["part"]), int(r["q_no"]), int(r["seq"]),
                    r["seg_type"], r["option_label"], r["text"])
        for r in read_csv(parsed / "listening_segments.csv")
    ]
    segments += [
        TextSegment("booklet", r["set_id"], r["section"], int(r["part"]), int(r["q_no"]), int(r["seq"]),
                    r["seg_type"], r["option_label"], r["text"])
        for r in read_csv(parsed / "booklet_segments.csv")
    ]
    corrected = {tuple(c[k] for k in PICTURE_KEY): c["corrected_text"] for c in read_csv(CORRECTIONS_PATH)}
    for r in read_csv(parsed / "image_ocr.csv"):
        if r["section"] == OCR_SECTION and int(r["part"]) == OCR_PART and int(r["n_zh"]) >= OCR_MIN_ZH:
            text = corrected.get(tuple(r[k] for k in PICTURE_KEY), r["ocr_text"])
            segments.append(TextSegment("ocr", r["set_id"], r["section"], int(r["part"]), int(r["q_no"]),
                                        int(r["img_idx"]), "picture", "", text))
    return [s for s in segments if s.text.strip()]


def segment_texts(texts: list[str]) -> tuple[list[list[str]], list[list[str]]]:
    """CKIP word segmentation, then POS tagging on the segmented words (one batch for all texts)."""
    ws = CkipWordSegmenter(model=CKIP_MODEL, device=-1)
    pos = CkipPosTagger(model=CKIP_MODEL, device=-1)
    words = ws(texts, use_delim=True)         # split long texts at punctuation -> better accuracy
    tags = pos(words)
    return words, tags


def to_tokens(segments: list[TextSegment], words: list[list[str]], tags: list[list[str]]) -> list[Token]:
    tokens: list[Token] = []
    for seg, ws, ps in zip(segments, words, tags, strict=True):
        if len(ws) != len(ps):
            raise ValueError(f"word/POS length mismatch in {seg.set_id} q{seg.q_no}: {ws}")
        for i, (w, p) in enumerate(zip(ws, ps), start=1):
            if w.strip():
                tokens.append(Token(seg.source, seg.set_id, seg.section, seg.part, seg.q_no, seg.seq, i, w, p))
    return tokens


def write_csv(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(r) for r in rows)


def main() -> None:
    cfg = load_config()
    parsed = ROOT / cfg["interim_dir"] / "parsed"

    segments = collect_segments(parsed)
    if not segments:
        raise ValueError("No text segments found — run steps 02-05 first")
    words, tags = segment_texts([s.text for s in segments])
    tokens = to_tokens(segments, words, tags)

    write_csv(parsed / "all_segments.csv", segments)
    write_csv(parsed / "tokens.csv", tokens)

    print(f"\n{'source':<9}{'segments':>9}{'chars':>8}{'tokens':>8}{'unique':>8}{'Nb':>6}")
    for source in ("script", "booklet", "ocr"):
        segs = [s for s in segments if s.source == source]
        toks = [t for t in tokens if t.source == source]
        words_only = [t for t in toks if not t.pos.endswith("CATEGORY")]       # drop punctuation tags
        print(f"{source:<9}{len(segs):>9}{sum(len(s.text) for s in segs):>8}{len(words_only):>8}"
              f"{len({t.token for t in words_only}):>8}{sum(t.pos == 'Nb' for t in toks):>6}")
    print(f"\nDone: {len(segments)} segments, {len(tokens)} tokens -> {parsed}")


if __name__ == "__main__":
    main()