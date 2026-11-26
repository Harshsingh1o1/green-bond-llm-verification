"""Run the offline end-to-end demonstration in a fresh directory."""
import argparse
import tempfile
from pathlib import Path

import pymupdf
from analyze_results import run_analysis
from evaluate import run_evaluation
from extract_pdf import extract_all_reports

EXAMPLES = Path(__file__).with_name("examples")
PAGES = [
["Demonstration Republic | Sovereign Green Bond Allocation and Impact Report",
 "Fictional issuer and figures for a software demonstration.",
 "Reporting period: year ended 31 March 2025. Published: 30 June 2025.",
 "All INR 100 crore was allocated: INR 60 crore to solar and INR 40 crore to rail.",
 "The closing unallocated balance was zero.",
 "Sunfield Solar Park, North District: INR 60 crore for solar generation.",
 "Riverline Electric Railway, East District: INR 40 crore for rail electrification.",
 "The framework excludes coal, oil and gas infrastructure.",
 "Sunfield generated 90,000 MWh. Riverline electrified 18 km of railway.",
 "Solar avoided emissions use a baseline grid factor of 0.7 tCO2e per MWh.",
 "This inaugural report uses the ICMA Harmonised Framework for Impact Reporting."],
["Governance and limitations",
 "The Green Bond Committee approves eligible expenditure each quarter.",
 "No external review of the framework or this report was commissioned.",
 "In the absence of bond financing, both projects would have proceeded on schedule.",
 "We claim no incremental access to finance from this issue.",
 "The issuer will publish an annual impact report until bond maturity.",
 "Land acquisition at Riverline displaced two businesses; compensation is pending.",
 "Stakeholders may submit grievances to the Treasury complaints desk."]]


def create_example(path):
    with pymupdf.open() as doc:
        for lines in PAGES:
            page = doc.new_page()
            for i, line in enumerate(lines):
                page.insert_text((35, 55 + 24*i), line, fontsize=10)
        doc.save(path)


def run_demo(output="demo-output"):
    dest = Path(output)
    if dest.exists():
        raise ValueError(f"{dest} exists; specify a fresh --output directory")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as temp:
        root = Path(temp) / "demo"
        reports = root / "reports"
        reports.mkdir(parents=True)
        create_example(reports / "fictional.pdf")
        extract_all_reports(reports, root / "text")
        run_evaluation(root / "text", root / "results", responses=EXAMPLES / "responses")
        run_analysis(root / "results", EXAMPLES / "illustrative_reference.csv")
        root.rename(dest)
    print(f"Demo saved to {dest}. Both sets of ratings are illustrative software fixtures.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="demo-output")
    args = parser.parse_args()
    try:
        run_demo(args.output)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Demo failed: {exc}\n")
