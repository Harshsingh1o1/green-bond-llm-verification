# extract_pdf.py
# Extracts and cleans text from all PDF reports in the /reports folder
# Run this first before evaluate.py

import fitz  # PyMuPDF
import os


def extract_text_from_pdf(pdf_path):
    """Extract and clean text from a single PDF file."""
    doc = fitz.open(pdf_path)
    full_text = ""

    for page in doc:
        text = page.get_text()
        full_text += text + "\n"

    doc.close()

    # Clean: remove excessive whitespace and empty lines
    lines = [line.strip() for line in full_text.splitlines()]
    lines = [line for line in lines if line]
    cleaned_text = "\n".join(lines)

    return cleaned_text


def extract_all_reports(reports_folder="reports", output_folder="extracted_text"):
    """Extract text from all PDFs in the reports folder."""

    os.makedirs(output_folder, exist_ok=True)
    extracted = {}

    pdf_files = [f for f in os.listdir(reports_folder) if f.endswith(".pdf")]

    if not pdf_files:
        print(f"No PDF files found in '{reports_folder}/' folder.")
        print("Please add your green bond impact report PDFs to that folder.")
        return {}

    print(f"Found {len(pdf_files)} PDF files.\n")

    for filename in sorted(pdf_files):
        pdf_path = os.path.join(reports_folder, filename)
        print(f"Extracting: {filename}")

        try:
            text = extract_text_from_pdf(pdf_path)
            report_name = filename.replace(".pdf", "")
            extracted[report_name] = text

            # Save as .txt for manual inspection
            output_path = os.path.join(output_folder, f"{report_name}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)

            char_count = len(text)
            word_count = len(text.split())
            print(f"  Saved: {output_path}")
            print(f"  Size: {char_count:,} characters / {word_count:,} words\n")

        except Exception as e:
            print(f"  ERROR extracting {filename}: {e}\n")

    print(f"Extraction complete. {len(extracted)} reports processed.")
    print(f"Check the extracted_text/ folder to verify quality before running evaluate.py")
    return extracted


if __name__ == "__main__":
    extract_all_reports()
