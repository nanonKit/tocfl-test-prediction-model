# OCR the pictures inside the test booklets.

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf
import yaml
from rapidocr_onnxruntime import RapidOCR

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "paths.yaml"

SECTION_BY_PREFIX = {"ls": "listening", "rd": "reading"}
RENDER_DPI = 300                         # OCR accuracy drops sharply below ~200 dpi
MIN_SIDE_PT = 40                         # skip icons / bullets smaller than this (PDF points)
TEXT_IMAGE_MIN_ZH = 5                    # >= 5 Chinese chars => "picture contains text" in the summary
RE_ZH = re.compile(r"[\u4e00-\u9fff]")
RE_QNUM_WORD = re.compile(r"^(\d{1,2})[.．]$")


@dataclass
class ImageText:
    set_id: str
    section: str
    part: int
    q_no: int
    page: int
    img_idx: int             # order of the picture on its page
    n_zh: int                # number of Chinese characters recognised
    confidence: float        # mean OCR score, 0-1
    ocr_text: str            # raw OCR output — never edited; fixes go to a separate corrections file


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_question_pages(path: Path) -> dict[tuple[str, str, int], dict[int, int]]:
    """(set, section, page) -> {q_no: part}, taken from the parsed booklet (example pages excluded)."""
    pages: dict[tuple[str, str, int], dict[int, int]] = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = (row["set_id"], row["section"], int(row["page"]))
            pages.setdefault(key, {})[int(row["q_no"])] = int(row["part"])
    return pages


def question_positions(page: pymupdf.Page) -> list[tuple[float, int]]:
    """(y, q_no) of every printed question number ("22.") on the page."""
    return [(w[1], int(m.group(1))) for w in page.get_text("words") if (m := RE_QNUM_WORD.match(w[4]))]


def nearest_question_above(y: float, positions: list[tuple[float, int]], allowed: dict[int, int]) -> int | None:
    """The picture belongs to the last question number printed at or above its top edge."""
    above = [(qy, q) for qy, q in positions if qy <= y + 5 and q in allowed]
    return max(above)[1] if above else min(allowed)          # fallback: picture above the first number


def ocr_page_images(ocr: RapidOCR, page: pymupdf.Page) -> list[tuple[pymupdf.Rect, str, float]]:
    results = []
    for info in page.get_image_info():
        rect = pymupdf.Rect(info["bbox"])
        if min(rect.width, rect.height) < MIN_SIDE_PT:
            continue
        png = page.get_pixmap(clip=rect, dpi=RENDER_DPI).tobytes("png")   # render what the reader sees
        lines, _ = ocr(png)
        text = "".join(line[1] for line in lines or [])
        score = sum(float(line[2]) for line in lines) / len(lines) if lines else 0.0
        results.append((rect, text, round(score, 3)))
    return results


def main() -> None:
    cfg = load_config()
    interim = ROOT / cfg["interim_dir"]
    out_path = interim / "parsed" / "image_ocr.csv"
    question_pages = load_question_pages(interim / "parsed" / "booklet_segments.csv")

    pdfs = sorted(Path(cfg["mock_dir"]).glob("mock*/*/*_tha_t.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No booklets under {cfg['mock_dir']}")

    ocr = RapidOCR()
    rows: list[ImageText] = []
    for pdf in pdfs:
        set_id, section = pdf.parent.parent.name, SECTION_BY_PREFIX[pdf.name[:2]]
        with pymupdf.open(pdf) as doc:
            for page in doc:
                allowed = question_pages.get((set_id, section, page.number + 1))
                if not allowed:                               # cover, instructions, worked examples
                    continue
                positions = question_positions(page)
                for idx, (rect, text, score) in enumerate(ocr_page_images(ocr, page), start=1):
                    q_no = nearest_question_above(rect.y0, positions, allowed)
                    rows.append(ImageText(set_id, section, allowed[q_no], q_no, page.number + 1,
                                          idx, len(RE_ZH.findall(text)), score, text))
        print(f"{set_id} {section:<10} {sum(r.set_id == set_id and r.section == section for r in rows):>4} pictures")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(r) for r in rows)

    print(f"\n{'section':<10}{'part':>5}{'pictures':>10}{'with_text':>11}{'zh_chars':>10}")
    for section, part in sorted({(r.section, r.part) for r in rows}):
        group = [r for r in rows if (r.section, r.part) == (section, part)]
        texty = [r for r in group if r.n_zh >= TEXT_IMAGE_MIN_ZH]
        print(f"{section:<10}{part:>5}{len(group):>10}{len(texty):>11}{sum(r.n_zh for r in texty):>10}")
    print(f"\nDone: {len(rows)} pictures -> {out_path}")


if __name__ == "__main__":
    main()