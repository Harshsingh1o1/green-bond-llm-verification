# analyze_results.py
# Compares your human scores against LLM scores
# Calculates agreement rates and Cohen's Kappa by dimension
# Run after evaluate.py and after filling in human_scores.csv

import pandas as pd
import os

# Try to import cohen_kappa_score
try:
    from sklearn.metrics import cohen_kappa_score
    SKLEARN_AVAILABLE = True
except ImportError:
    print("Note: scikit-learn not installed. Kappa scores will not be calculated.")
    print("Install with: pip install scikit-learn")
    SKLEARN_AVAILABLE = False

# Which criteria belong to which dimension
DIMENSION_MAP = {
    "C1": "D1", "C2": "D1", "C3": "D1", "C4": "D1", "C5": "D1",
    "C6": "D2", "C7": "D2", "C8": "D2", "C9": "D2", "C10": "D2", "C11": "D2",
    "C12": "D3", "C13": "D3", "C14": "D3", "C15": "D3",
    "C16": "D4", "C17": "D4", "C18": "D4", "C19": "D4", "C20": "D4",
    "C21": "D5", "C22": "D5", "C23": "D5", "C24": "D5", "C25": "D5", "C26": "D5"
}

DIMENSION_NAMES = {
    "D1": "Use of Proceeds & Allocation Transparency",
    "D2": "Impact Metrics & Measurement Quality",
    "D3": "Additionality Evidence",
    "D4": "Third-Party Verification & Governance",
    "D5": "Transparency, Accessibility & Ongoing Disclosure"
}

SCORE_MAP = {"FM": 0, "PM": 1, "NM": 2, "CD": 3}
VALID_SCORES = {"FM", "PM", "NM", "CD"}


def create_human_scores_template(llm_df):
    """Create a blank human_scores.csv template from LLM scores."""
    template_path = "results/human_scores.csv"

    if os.path.exists(template_path):
        print(f"human_scores.csv already exists. Not overwriting.")
        return

    template = llm_df[["report", "criterion_id"]].copy()
    template["human_score"] = ""
    template.to_csv(template_path, index=False)

    print(f"Created template: {template_path}")
    print(f"Open this file in Excel, fill in the human_score column")
    print(f"Use only: FM / PM / NM / CD")
    print(f"Save as CSV when done, then run this script again.")


def calculate_agreement_by_dimension(merged_df):
    """Calculate agreement rate and Kappa for each dimension."""
    results = []

    for dim_id, dim_name in DIMENSION_NAMES.items():
        dim_criteria = [c for c, d in DIMENSION_MAP.items() if d == dim_id]
        dim_df = merged_df[merged_df["criterion_id"].isin(dim_criteria)].copy()

        # Keep only valid scores
        dim_df = dim_df[
            dim_df["human_score"].isin(VALID_SCORES) &
            dim_df["llm_score"].isin(VALID_SCORES)
        ]

        if len(dim_df) == 0:
            continue

        # Agreement rate
        agree = (dim_df["human_score"] == dim_df["llm_score"]).sum()
        total = len(dim_df)
        agreement_pct = round(agree / total * 100, 1)

        # Cohen's Kappa
        kappa = "N/A"
        if SKLEARN_AVAILABLE and len(dim_df) >= 5:
            try:
                human_numeric = dim_df["human_score"].map(SCORE_MAP)
                llm_numeric = dim_df["llm_score"].map(SCORE_MAP)
                kappa = round(cohen_kappa_score(human_numeric, llm_numeric), 2)
            except Exception as e:
                kappa = f"Error: {e}"

        results.append({
            "Dimension ID": dim_id,
            "Dimension Name": dim_name,
            "Total Evaluations": total,
            "Agreements": agree,
            "Agreement (%)": agreement_pct,
            "Cohen's Kappa": kappa
        })

    return pd.DataFrame(results)


def analyze_failure_modes(merged_df):
    """Save disagreements for manual failure mode classification."""

    disagreements = merged_df[
        merged_df["human_score"] != merged_df["llm_score"]
    ].copy()

    disagreements["dimension"] = disagreements["criterion_id"].map(DIMENSION_MAP)

    # Add empty column for manual classification
    disagreements["failure_mode"] = ""
    disagreements["failure_mode_notes"] = ""

    output_path = "results/disagreements_for_classification.csv"
    disagreements.to_csv(output_path, index=False)

    print(f"\nDisagreements saved: {output_path}")
    print(f"Total disagreements: {len(disagreements)}")
    print(f"\nOpen this file and classify each row as one of:")
    print(f"  T1_Hallucination     - LLM asserted facts not in the report")
    print(f"  T2_Over_optimism     - LLM scored too high without evidence")
    print(f"  T3_Context_Limitation - LLM used CD where human could determine score")
    print(f"  T4_Structural_Miss   - LLM misread document structure or PDF artifacts")

    return disagreements


def run_analysis():
    """Run the full agreement analysis."""

    print("=" * 60)
    print("AGREEMENT ANALYSIS")
    print("=" * 60)

    # Check files exist
    llm_path = "results/llm_scores.csv"
    human_path = "results/human_scores.csv"

    if not os.path.exists(llm_path):
        print(f"ERROR: {llm_path} not found.")
        print("Please run evaluate.py first.")
        return

    # Load LLM scores
    llm_df = pd.read_csv(llm_path)
    print(f"\nLLM scores loaded: {len(llm_df)} rows")

    # If human scores don't exist, create template
    if not os.path.exists(human_path):
        print(f"\nhuman_scores.csv not found.")
        print("Creating a blank template for you to fill in...")
        create_human_scores_template(llm_df)
        return

    # Load human scores
    human_df = pd.read_csv(human_path)
    human_df = human_df[human_df["human_score"].isin(VALID_SCORES)]
    print(f"Human scores loaded: {len(human_df)} rows with valid scores")

    if len(human_df) == 0:
        print("\nNo valid human scores found yet.")
        print("Please fill in the human_score column in results/human_scores.csv")
        print("Valid values: FM / PM / NM / CD")
        return

    # Merge
    merged = pd.merge(
        llm_df[["report", "criterion_id", "llm_score", "llm_justification"]],
        human_df[["report", "criterion_id", "human_score"]],
        on=["report", "criterion_id"],
        how="inner"
    )

    print(f"Matched evaluations: {len(merged)}")
    print(f"Reports covered: {merged['report'].nunique()}")

    # Overall agreement
    valid = merged[
        merged["human_score"].isin(VALID_SCORES) &
        merged["llm_score"].isin(VALID_SCORES)
    ]
    overall_agree = (valid["human_score"] == valid["llm_score"]).mean() * 100
    print(f"\nOverall agreement rate: {overall_agree:.1f}%")

    # By dimension
    print("\nAgreement by dimension:")
    dim_results = calculate_agreement_by_dimension(merged)
    print(dim_results.to_string(index=False))

    # Save
    os.makedirs("results", exist_ok=True)
    dim_results.to_csv("results/agreement_by_dimension.csv", index=False)
    print(f"\nSaved: results/agreement_by_dimension.csv")

    # Score distribution comparison
    print("\nScore distribution comparison:")
    for score in ["FM", "PM", "NM", "CD"]:
        human_count = (valid["human_score"] == score).sum()
        llm_count = (valid["llm_score"] == score).sum()
        human_pct = human_count / len(valid) * 100
        llm_pct = llm_count / len(valid) * 100
        print(f"  {score}: Human={human_pct:.1f}%  LLM={llm_pct:.1f}%")

    # Failure mode analysis
    analyze_failure_modes(merged)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nFiles ready for the paper:")
    print(f"  results/agreement_by_dimension.csv")
    print(f"  results/disagreements_for_classification.csv")


if __name__ == "__main__":
    run_analysis()
