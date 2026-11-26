"""Compare paired nominal ratings, including CD as a rating category."""
import argparse
import csv
from collections import Counter
from pathlib import Path

from evaluate import load_rubric, write_csv


def read_scores(path, column, rubric, allow_blanks=False):
    ids = {c["id"] for d in rubric["dimensions"] for c in d["criteria"]}
    rows = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as src:
        reader = csv.DictReader(src)
        if not {"report", "criterion_id", column} <= set(reader.fieldnames or []):
            raise ValueError(f"Missing columns in {path}")
        for row in reader:
            key = (row["report"], row["criterion_id"])
            score = (row[column] or "").strip().upper()
            if not key[0] or key[1] not in ids or key in rows:
                raise ValueError(f"Invalid or duplicate report/criterion in {path}: {key}")
            if score not in rubric["scoring_scale"] and not (allow_blanks and score == ""):
                raise ValueError(f"Invalid score in {path} for {key}: {score}")
            row[column] = score
            rows[key] = row
    if not rows:
        raise ValueError(f"No data in {path}")
    if not allow_blanks:
        for report in {name for name, _ in rows}:
            if {cid for name, cid in rows if name == report} != ids:
                raise ValueError(f"Incomplete score set for {report}")
    return rows


def summarize(pairs):
    n = len(pairs)
    agree = sum(a == b for a, b in pairs)
    a_counts, b_counts = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    chance_numerator = sum(n_a * b_counts[a] for a, n_a in a_counts.items())
    denom = n*n - chance_numerator
    return {"Total Evaluations": n, "Agreements": agree,
            "Agreement (%)": round(100*agree/n, 1) if n else "N/A",
            "Cohen's Kappa": round((n*agree - chance_numerator)/denom, 4) if denom else "N/A"}


def run_analysis(results="results", human=None):
    folder = Path(results)
    rubric = load_rubric()
    llm = read_scores(folder / "llm_scores.csv", "llm_score", rubric)
    human_path = Path(human) if human else folder / "human_scores.csv"
    if human is None and not human_path.exists():
        write_csv(human_path, [dict(report=r, criterion_id=c, human_score="") for r, c in llm])
        print(f"Fill the independent review template at {human_path} and rerun.")
        return
    ratings = read_scores(human_path, "human_score", rubric, allow_blanks=True)
    if ratings.keys() - llm.keys():
        raise ValueError("Reference file contains keys absent from this evaluation")
    pairs = {k: (row["human_score"], llm[k]["llm_score"]) for k, row in ratings.items() if row["human_score"]}
    if not pairs:
        raise ValueError("No paired ratings yet")
    summary = [{"Dimension ID": "ALL", "Dimension Name": "Overall", **summarize(pairs.values())}]
    for dim in rubric["dimensions"]:
        ids = {c["id"] for c in dim["criteria"]}
        subset = [pair for (_, c), pair in pairs.items() if c in ids]
        summary.append({"Dimension ID": dim["id"], "Dimension Name": dim["name"], **summarize(subset)})
    fields = ["report", "criterion_id", "human_score", "llm_score", "llm_justification",
              "page", "quote", "failure_mode", "failure_mode_notes"]
    disagreement_path = folder / "disagreements_for_classification.csv"
    # Keep previous manual work separate when refreshing the machine-generated export.
    if disagreement_path.exists():
        with disagreement_path.open(encoding="utf-8-sig", newline="") as previous:
            if any(row.get("failure_mode") or row.get("failure_mode_notes") for row in csv.DictReader(previous)):
                raise ValueError(f"Archive annotated {disagreement_path} before regenerating outputs")
    write_csv(folder / "agreement_by_dimension.csv", summary)
    with disagreement_path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for key, (reference, score) in pairs.items():
            if reference != score:
                writer.writerow(dict(llm[key], human_score=reference))
    print(f"Paired {len(pairs)}/{len(llm)} rows; {summary[0]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results")
    parser.add_argument("--human", help="CSV with report,criterion_id,human_score")
    args = parser.parse_args()
    try:
        run_analysis(**vars(args))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Analysis failed: {exc}\n")
