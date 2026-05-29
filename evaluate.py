# evaluate.py
# Sends each report to GPT-4o for evaluation against the 26-criterion rubric
# Run after extract_pdf.py

import os
import json
import csv
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_rubric(rubric_path="rubric.json"):
    """Load the rubric from JSON file."""
    with open(rubric_path, "r") as f:
        return json.load(f)


def build_rubric_text(rubric):
    """Convert rubric JSON into readable text for the prompt."""
    rubric_text = ""
    for dim in rubric["dimensions"]:
        rubric_text += f"\n=== {dim['id']}: {dim['name']} ===\n"
        for criterion in dim["criteria"]:
            rubric_text += f"\n{criterion['id']}. {criterion['name']}\n"
            rubric_text += f"   {criterion['description']}\n"
    return rubric_text


def load_extracted_reports(extracted_folder="extracted_text"):
    """Load all extracted text files."""
    reports = {}

    txt_files = [f for f in os.listdir(extracted_folder) if f.endswith(".txt")]

    if not txt_files:
        print(f"No .txt files found in '{extracted_folder}/'")
        print("Please run extract_pdf.py first.")
        return {}

    for filename in sorted(txt_files):
        report_name = filename.replace(".txt", "")
        filepath = os.path.join(extracted_folder, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            reports[report_name] = f.read()

    return reports


def build_prompt(rubric_text, report_text):
    """Build the exact prompt sent to GPT-4o."""

    # Truncate if report is very long (GPT-4o context limit)
    max_chars = 80000
    if len(report_text) > max_chars:
        report_text = report_text[:max_chars]
        report_text += "\n\n[NOTE: Report truncated at 80,000 characters due to length]"

    prompt = f"""You are an expert green bond auditor trained on ICMA Green Bond Principles and the RBI Sovereign Green Bond Framework.

You will evaluate the following impact report against 26 pre-defined criteria.

For EACH criterion, respond with EXACTLY this format on a single line:
CRITERION_ID | SCORE | One sentence of justification

Rules:
- SCORE must be exactly one of: FM / PM / NM / CD
- FM = Fully Met
- PM = Partially Met  
- NM = Not Met
- CD = Cannot Determine (use when the report does not contain enough information)
- Evaluate all 26 criteria in order (C1 through C26)
- Do not skip any criterion
- Do not add headers, preamble, or any text outside the required format

=== EVALUATION CRITERIA ===
{rubric_text}

=== REPORT TEXT ===
{report_text}

=== YOUR EVALUATION ==="""

    return prompt


def parse_llm_response(response_text, report_name):
    """Parse the LLM response into structured rows."""
    rows = []
    valid_scores = {"FM", "PM", "NM", "CD"}
    parse_errors = 0

    for line in response_text.strip().splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue

        parts = line.split("|", 2)
        if len(parts) < 3:
            continue

        criterion_id = parts[0].strip()
        score = parts[1].strip().upper()
        justification = parts[2].strip()

        # Clean up criterion ID if model added extra text
        criterion_id = criterion_id.split(".")[0].strip()

        if score not in valid_scores:
            score = "PARSE_ERROR"
            parse_errors += 1

        rows.append({
            "report": report_name,
            "criterion_id": criterion_id,
            "llm_score": score,
            "llm_justification": justification
        })

    if parse_errors > 0:
        print(f"  Warning: {parse_errors} lines could not be parsed correctly")

    return rows


def evaluate_single_report(report_name, report_text, rubric_text):
    """Send one report to GPT-4o and return parsed results."""

    prompt = build_prompt(rubric_text, report_text)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a precise green bond auditor. Follow the output format exactly. Evaluate every criterion. Do not skip any."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=3000
    )

    response_text = response.choices[0].message.content
    rows = parse_llm_response(response_text, report_name)

    return rows, response_text


def run_evaluation():
    """Run the full evaluation pipeline."""

    print("=" * 60)
    print("GREEN BOND LLM EVALUATION PIPELINE")
    print("=" * 60)

    # Load rubric
    print("\nStep 1: Loading rubric...")
    rubric = load_rubric()
    rubric_text = build_rubric_text(rubric)
    total_criteria = sum(len(d["criteria"]) for d in rubric["dimensions"])
    print(f"Loaded: {total_criteria} criteria across {len(rubric['dimensions'])} dimensions")

    # Load extracted reports
    print("\nStep 2: Loading extracted reports...")
    reports = load_extracted_reports()
    if not reports:
        return
    print(f"Loaded: {len(reports)} reports")

    # Create output folder
    os.makedirs("results", exist_ok=True)
    all_rows = []
    raw_responses = {}
    failed_reports = []

    # Evaluate each report
    print(f"\nStep 3: Evaluating reports with GPT-4o...")
    print(f"This will make {len(reports)} API calls. Estimated cost: $5-15 total.\n")

    for i, (report_name, report_text) in enumerate(reports.items(), 1):
        print(f"[{i}/{len(reports)}] {report_name}")

        try:
            rows, raw_response = evaluate_single_report(
                report_name, report_text, rubric_text
            )
            all_rows.extend(rows)
            raw_responses[report_name] = raw_response
            print(f"  Got {len(rows)} criterion scores")

            # Pause between calls to avoid rate limits
            if i < len(reports):
                print(f"  Pausing 3 seconds...")
                time.sleep(3)

        except Exception as e:
            print(f"  ERROR: {e}")
            failed_reports.append(report_name)
            continue

    # Save LLM scores to CSV
    output_csv = "results/llm_scores.csv"
    fieldnames = ["report", "criterion_id", "llm_score", "llm_justification"]

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    # Save raw responses for audit trail
    with open("results/raw_llm_responses.json", "w", encoding="utf-8") as f:
        json.dump(raw_responses, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Total criterion scores recorded: {len(all_rows)}")
    print(f"Reports evaluated successfully: {len(reports) - len(failed_reports)}")
    if failed_reports:
        print(f"Failed reports: {failed_reports}")
    print(f"\nOutputs saved:")
    print(f"  results/llm_scores.csv        (main output)")
    print(f"  results/raw_llm_responses.json (audit trail)")
    print(f"\nNext step: Fill in results/human_scores.csv with your manual scores")
    print(f"Then run: python analyze_results.py")


if __name__ == "__main__":
    run_evaluation()
