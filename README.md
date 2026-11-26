# Green Bond LLM Verification

A Python review tool for sovereign green bond allocation and impact reports. It pairs each supported rubric score with a quotation and its physical PDF page, then compares model and human judgments. A reviewer can inspect the source, the score rationale and any disagreement in a spreadsheet.

Research project by Harsh Singh accompanying *Can LLMs Detect Greenwashing? Evaluating AI-Assisted Verification of Sovereign Green Bond Impact Reports in India*.

## Run the offline demo

From the repository root on macOS or Linux with Python 3.11 or later:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python demo.py
python -m unittest -v
```

The demo generates a fictional two-page PDF, extracts its text, validates a saved example response and compares it with illustrative reference ratings. It runs offline after installation, with no API key. For another run, choose a fresh folder with `python demo.py --output demo-2`.

| Inspect | What to look for |
|---|---|
| `demo-output/reports/fictional.pdf` | The source document. Page 2 explicitly says that external review was never commissioned. |
| `demo-output/results/llm_scores.csv` | One row per criterion. C16 is NM, with the statement above quoted from page 2. C21 is CD because the document alone cannot establish whether it is publicly accessible. |
| `demo-output/results/manifest.json` | Input text fingerprint, physical page count and response origin. |
| `demo-output/results/agreement_by_dimension.csv` | Paired counts, exact agreement and unweighted Cohen’s kappa overall and by dimension. |
| `demo-output/results/disagreements_for_classification.csv` | The two deliberately different reference ratings, C8 and C15, ready for reviewer notes. |

The example has 24 matching labels out of 26. Both rating sets were prepared for demonstration. A study of model performance requires independently coded reports and recorded model runs.

## Review a report

1. Put text-based PDFs in `reports/`, then run `python extract_pdf.py`. Inspect the extracted UTF-8 files in `extracted_text/`. Form-feed characters separate physical PDF pages, including blank pages. Table layout can change during extraction, and image-only pages need OCR upstream.
2. For a live evaluation, set `OPENAI_API_KEY` in your environment or a local `.env` file and run `python evaluate.py`. This sends the report text and rubric to OpenAI using the selected model and may incur API charges. The default model is `gpt-4o`; `--model` selects another Chat Completions model supporting JSON objects.
3. For manual model use, export prompts with `python evaluate.py --prompts --output prompts`. Submit each prompt to your chosen model. Save its JSON reply as `responses/<report-name>.json`, then run `python evaluate.py --responses responses --output results`. The provided fixture shows the required response format. Imported runs record their origin as imported. Record the model and date separately when conducting research.
4. Run `python analyze_results.py` to produce a blank `results/human_scores.csv`. Have a reviewer assign ratings independently using the report and rubric, then rerun the command. Blank ratings are excluded from paired counts. CD is a substantive category. Kappa is reported as N/A when undefined.
5. Open the disagreement export to investigate differences. Keep manual classifications in a separate copy. Use fresh extraction and evaluation output directories for subsequent runs.

Each supported rating (FM, PM or NM) needs a quote that matches its cited page after whitespace normalization. CD requires a rationale and no supporting quote. Validation rejects duplicate or missing criteria, invalid labels, mismatched input fingerprints and unmatched quotations. It also rejects inputs longer than 80,000 characters before requesting inference. For a scoped review, label an excerpt explicitly and interpret its page numbers relative to that excerpt. For previously extracted flat text, rerun extraction on the original PDF to recover physical page numbers.

A matching quotation establishes that the passage exists. A reviewer still decides whether it supports the score, whether the disclosure is accurate and whether claimed environmental impact is independently verified. In a separate manual-model run on section 3.6 of India’s FY 2022–23 Sovereign Green Bonds Impact Report, the importer accepted three page-cited ratings and 23 “cannot determine” ratings. The excerpt identified a framework opinion provider and the scope of allocation verification. Its wording leaves the reviewer’s accreditation and assurance of impact figures unresolved. This exercise covered one excerpt and had no independent human benchmark. [Government of India source report](https://dea.gov.in/files/other_reports_documents/Impact%20Report%2022-23%20Spread%20%2818-02-2026%29-Final.pdf)

## Rubric Overview

The 26-criterion rubric covers five dimensions:

| Dimension | Criteria | Weight |
|-----------|----------|--------|
| D1: Use of Proceeds & Allocation Transparency | 5 | 25% |
| D2: Impact Metrics & Measurement Quality | 6 | 25% |
| D3: Additionality Evidence | 4 | 20% |
| D4: Third-Party Verification & Governance | 5 | 20% |
| D5: Transparency, Accessibility & Disclosure | 6 | 10% |

Each criterion scored as: FM / PM / NM / CD

---

## Citation

If you use this rubric or pipeline in your research, please cite:

Singh, H. (2025). Can LLMs detect greenwashing? Evaluating 
AI-assisted verification of sovereign green bond impact reports 
in India. SSRN Working Paper.

https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6851501



---

## License
MIT License — free to use with attribution.
