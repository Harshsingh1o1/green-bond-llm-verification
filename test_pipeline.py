"""Regression checks for the review workflow and its evidence boundary."""
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf

from analyze_results import run_analysis, summarize
from demo import create_example, run_demo, EXAMPLES
from evaluate import call_openai, load_rubric, parse_response, prompt_for, run_evaluation, source_hash
from extract_pdf import extract_text_from_pdf


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.pdf = self.root / "fictional.pdf"
        create_example(self.pdf)
        self.text = extract_text_from_pdf(self.pdf)
        self.rubric = load_rubric()
        self.raw = (EXAMPLES / "responses" / "fictional.json").read_text()
        self.data = json.loads(self.raw)

    def test_end_to_end_demo(self):
        dest = self.root / "demo"
        run_demo(dest)
        with (dest / "results" / "agreement_by_dimension.csv").open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual((len(rows), rows[0]["Agreements"], rows[0]["Cohen's Kappa"]), (6, "24", "0.8744"))
        with (dest / "results" / "disagreements_for_classification.csv").open() as f:
            self.assertEqual({row["criterion_id"] for row in csv.DictReader(f)}, {"C8", "C15"})

    def test_incomplete_duplicate_unknown_and_invalid_ratings(self):
        for change in ("missing", "duplicate", "unknown", "score", "empty reason", "CD with evidence"):
            with self.subTest(change=change):
                data = json.loads(self.raw)
                rows = data["assessments"]
                if change == "missing":
                    rows.pop()
                elif change == "duplicate":
                    rows.append(rows[0])
                elif change == "unknown":
                    rows[0]["criterion_id"] = "C27"
                elif change == "score":
                    rows[0]["score"] = "maybe"
                elif change == "empty reason":
                    rows[0]["justification"] = ""
                else:
                    rows[0]["score"] = "CD"
                with self.assertRaises(ValueError):
                    parse_response(json.dumps(data), "fixture", self.text, self.rubric)

    def test_wrong_page_and_fabricated_quote(self):
        for edit in ({"page": 2}, {"page": 9}, {"quote": "Fabricated disclosure"}):
            with self.subTest(edit=edit):
                data = json.loads(self.raw)
                data["assessments"][0].update(edit)
                with self.assertRaises(ValueError):
                    parse_response(json.dumps(data), "fixture", self.text, self.rubric)

    def test_source_fingerprint(self):
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            parse_response(self.raw, "fixture", self.text + " revision", self.rubric)

    def test_missing_text_and_size_limits(self):
        blank = self.root / "empty.pdf"
        with pymupdf.open() as doc:
            doc.new_page()
            doc.save(blank)
        with self.assertRaisesRegex(ValueError, "OCR"):
            extract_text_from_pdf(blank)
        for text in (" ", "x"*80_001):
            with self.assertRaises(ValueError):
                prompt_for(text, self.rubric)

    def test_failed_batch_leaves_no_published_results(self):
        (self.root / "fictional.txt").write_text(self.text)
        (self.root / "z_missing_response.txt").write_text("second report")
        dest = self.root / "results"
        with self.assertRaises(FileNotFoundError):
            run_evaluation(self.root, dest, EXAMPLES / "responses")
        self.assertFalse(dest.exists())

    def test_api_request_and_response_with_mock_transport(self):
        (self.root / "fictional.txt").write_text(self.text)
        dest = self.root / "live"
        reply = {"model": "mock-model", "choices": [{"finish_reason": "stop", "message": {"content": self.raw}}]}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-placeholder"}):
            with patch("evaluate.urlopen", return_value=io.BytesIO(json.dumps(reply).encode())) as send:
                run_evaluation(self.root, dest)
        req = send.call_args.args[0]
        self.assertEqual(req.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(json.loads(req.data)["response_format"]["type"], "json_object")
        self.assertEqual(json.loads((dest / "manifest.json").read_text())["fictional"]["model"], "mock-model")
        reply["choices"][0]["finish_reason"] = "length"
        with patch("evaluate.urlopen", return_value=io.BytesIO(json.dumps(reply).encode())):
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                call_openai("prompt", "model", "test-placeholder")

    def test_prompt_export_and_duplicate_reference(self):
        (self.root / "fictional.txt").write_text(self.text)
        run_evaluation(self.root, self.root / "prompts", prompts=True)
        self.assertIn(source_hash(self.text), (self.root / "prompts" / "fictional.txt").read_text())
        dest = self.root / "results"
        run_evaluation(self.root, dest, EXAMPLES / "responses")
        run_analysis(dest)
        ref = dest / "human_scores.csv"
        with ref.open("a") as f:
            f.write("fictional,C1,PM\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            run_analysis(dest)

    def test_kappa_edge_cases(self):
        self.assertEqual(summarize([("FM", "FM")])["Cohen's Kappa"], "N/A")
        self.assertEqual(summarize([])["Agreement (%)"], "N/A")
        self.assertEqual(summarize([("FM", "PM"), ("PM", "FM")])["Cohen's Kappa"], -1)

    def test_government_excerpt_has_limited_scope(self):
        # Government of India, Sovereign Green Bonds Impact Report FY 2022-23, section 3.6.
        # A framework opinion cannot establish that impact figures received assurance.
        excerpt = "The framework has received a Second Party Opinion from CICERO"
        ratings = [dict(criterion_id=c["criterion_id"], score="CD", page=None, quote="",
                        justification="Insufficient evidence in this excerpt.") for c in self.data["assessments"]]
        ratings[16].update(score="PM", page=1, quote=excerpt, justification="Reviewer named; accreditation unspecified.")
        payload = json.dumps(dict(source_sha256=source_hash(excerpt), assessments=ratings))
        result = parse_response(payload, "section_3_6_excerpt", excerpt, self.rubric)
        self.assertEqual((result[16]["llm_score"], result[16]["page"]), ("PM", 1))


if __name__ == "__main__":
    unittest.main()
