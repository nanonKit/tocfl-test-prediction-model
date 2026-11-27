# Measure OCR quality against the human-reviewed corrections.

import csv
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "paths.yaml"
CORRECTIONS_PATH = ROOT / "data" / "manual" / "ocr_corrections.csv"
KEY = ("set_id", "section", "page", "img_idx")
RE_ZH = re.compile(r"[\u4e00-\u9fff]")


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def chinese_only(text: str) -> str:
    """Compare Chinese characters only: punctuation and digits are noise for a vocabulary project."""
    return "".join(RE_ZH.findall(text))


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance (insert / delete / substitute = 1), two-row dynamic programming."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


def main() -> None:
    cfg = load_config()
    ocr_rows = {tuple(r[k] for k in KEY): r for r in read_csv(ROOT / cfg["interim_dir"] / "parsed" / "image_ocr.csv")}
    corrections = read_csv(CORRECTIONS_PATH)

    unmatched = [c for c in corrections if tuple(c[k] for k in KEY) not in ocr_rows]
    if unmatched:
        raise ValueError(f"{len(unmatched)} corrections do not match any OCR row, first = {unmatched[0]}")

    totals: dict[str, list[int]] = {}                  # set_id -> [errors, reference chars, pictures]
    for c in corrections:
        ocr = chinese_only(ocr_rows[tuple(c[k] for k in KEY)]["ocr_text"])
        ref = chinese_only(c["corrected_text"])
        t = totals.setdefault(c["set_id"], [0, 0, 0])
        t[0] += edit_distance(ocr, ref)
        t[1] += len(ref)
        t[2] += 1

    print(f"{'set':<8}{'pictures':>9}{'zh_chars':>10}{'errors':>8}{'CER':>8}")
    for set_id, (err, n, pics) in sorted(totals.items()):
        print(f"{set_id:<8}{pics:>9}{n:>10}{err:>8}{err / n:>8.1%}")
    err, n, pics = (sum(t[i] for t in totals.values()) for i in range(3))
    print(f"{'ALL':<8}{pics:>9}{n:>10}{err:>8}{err / n:>8.1%}")


if __name__ == "__main__":
    main()