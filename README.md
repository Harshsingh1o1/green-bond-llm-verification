# Green Bond LLM Verification

**Replication package for:**
"Can LLMs Detect Greenwashing? Evaluating AI-Assisted 
Verification of Sovereign Green Bond Impact Reports in India"

Author: Harsh Singh, singh.harsh.live@gmail.com

---

## What This Repository Contains

| File | Purpose |
|------|---------|
| `rubric.json` | 26-criterion evaluation rubric (machine-readable) |
| `extract_pdf.py` | Extracts text from PDF impact reports |
| `evaluate.py` | Runs GPT-4o evaluation against the rubric |
| `analyze_results.py` | Calculates agreement rates and Cohen's Kappa |

---

## How to Use

### 1. Install dependencies
pip install openai anthropic pymupdf pandas openpyxl python-dotenv scikit-learn

### 2. Add your API keys
Create a .env file in the root folder:
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

### 3. Add your PDF reports
Place all green bond impact report PDFs in the reports/ folder.

### 4. Run in order
python extract_pdf.py
python evaluate.py
python analyze_results.py

---

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
https://ssrn.com/abstract=[your_new_ssrn_id]

---

## License
MIT License — free to use with attribution.
