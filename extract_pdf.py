"""Extract PDFs into UTF-8 text with one form-feed between physical pages."""
import argparse
from pathlib import Path

import pymupdf


def extract_text_from_pdf(pdf_path):
    with pymupdf.open(pdf_path) as doc:
        if doc.needs_pass:
            raise ValueError(f"{pdf_path}: password-protected PDF")
        pages = [page.get_text(sort=True).strip() for page in doc]
    if not any(pages):
        raise ValueError(f"{pdf_path}: no selectable text; run OCR first")
    blank = [str(i) for i, page in enumerate(pages, 1) if not page]
    if blank:
        print(f"{pdf_path}: pages without selectable text: {', '.join(blank)}")
    return "\f".join(pages)


def extract_all_reports(reports_folder="reports", output_folder="extracted_text"):
    source, dest = Path(reports_folder), Path(output_folder)
    files = sorted(p for p in source.glob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    if not files:
        raise ValueError(f"Place a text-based PDF in {source}/ or run python demo.py")
    if dest.exists() and any(dest.glob("*.txt")):
        raise ValueError(f"Choose a fresh extraction directory with --output ({dest} contains text)")
    reports = {}
    for path in files:
        if path.stem in reports:
            raise ValueError(f"Duplicate report name: {path.stem}")
        reports[path.stem] = extract_text_from_pdf(path)
    dest.mkdir(parents=True, exist_ok=True)
    for name, text in reports.items():
        (dest / f"{name}.txt").write_text(text, encoding="utf-8")
        print(f"{name}: {len(text.split(chr(12)))} PDF pages")
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--output", default="extracted_text")
    args = parser.parse_args()
    try:
        extract_all_reports(args.reports, args.output)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Extraction failed: {exc}\n")
