# Extract text from pdf files and save to txt files

from pathlib import Path

import pymupdf
import yaml

ROOT = Path(__file__).resolve().parents[1]                   # finding repo root src/... >> not crash when change the directory
CONFIG_PATH = ROOT / "config" / "paths.yaml"
SECTION = {"listening", "reading"}                          # skip score_table, audio

def load_config(path: Path = CONFIG_PATH) -> dict:          # reading yaml path >> even through adjusted folder name, just edit only yaml file, not the code
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def find_pdfs(mock_dir: Path) -> list[Path]:                # find pdf files in the given directory
    """All PDFs under mock0X/listening and mock0X/reading, sorted for stable order."""
    pdfs = [p for p in mock_dir.glob("mock*/*/*.pdf") if p.parent.name in SECTION]         # finding pdf in deep layers
    return sorted(pdfs)                                                                     # sorting pdf files


def extract_pdf(pdf_path: Path) -> tuple[str, int]:         # extract text from pdf file
    """Return (text with '=== page N ===) markers, page count)."""
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            pages.append(f"=== page {i} ===\n{page.get_text()}")
        n_pages = doc.page_count
    return "\n".join(pages), n_pages


def main() -> None:
    cfg = load_config()
    mock_dirs = Path(cfg["mock_dir"])
    out_root = ROOT / cfg["interim_dir"] / "text"

    pdfs = find_pdfs(mock_dirs)
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in {mock_dirs}")

    print(f"{'set':<7}{'section':<11}{'file':<36}{'pages':>6}{'chars':>8}")
    for pdf in pdfs:
        set_id = pdf.parent.parent.name                     # .../mock01/listening/01.pdf >> mock01
        section = pdf.parent.name                           
        text, n_pages = extract_pdf(pdf)

        out_path = out_root / set_id / f"{pdf.stem}.txt"          # .../interim/text/mock01/01.txt
        out_path.parent.mkdir(parents=True, exist_ok=True)        # create parent directory if not exist
        out_path.write_text(text, encoding="utf-8")               # overwrite: output is derived, always reproducible

        print(f"{set_id:<7}{section:<11}{pdf.name:<36}{n_pages:>6}{len(text):>8}")

    print(f"\nDone: {len(pdfs)} files -> {out_root}")


if __name__ == "__main__":
    main()