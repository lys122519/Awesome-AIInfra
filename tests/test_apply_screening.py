import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import yaml

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import apply_screening  # noqa: E402


class ApplyScreeningTests(unittest.TestCase):
    def test_accept_only_applies_accepts_and_leaves_rejects_unrecorded(self):
        token = uuid4().hex
        paths = [ROOT / "tests" / f".tmp-{token}-{name}.yaml" for name in ("papers", "rejected", "decisions")]
        papers_path, rejected_path, decisions_path = paths
        try:
            papers_path.write_text("papers: []\n", encoding="utf-8")
            rejected_path.write_text("rejected: []\n", encoding="utf-8")
            decisions_path.write_text(
                yaml.safe_dump(
                    {
                        "decisions": [
                            {
                                "title": "Fast LLM Serving",
                                "year": 2026,
                                "venue": "MLSys",
                                "category": "Inference and Serving",
                                "publication": "https://example.com/accepted",
                                "source": "tracker",
                                "reviewed": False,
                                "decision": "accept",
                                "reason": "direct systems contribution",
                            },
                            {
                                "title": "Ambiguous Candidate",
                                "year": 2026,
                                "venue": "ICML",
                                "category": "Efficient LLM Systems",
                                "publication": "https://example.com/review",
                                "source": "tracker",
                                "reviewed": False,
                                "decision": "reject",
                                "reason": "insufficient title evidence",
                            },
                        ]
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            with (
                patch.object(apply_screening, "PAPERS_PATH", papers_path),
                patch.object(apply_screening, "REJECTED_PATH", rejected_path),
            ):
                result = apply_screening.apply_decisions(
                    decisions_path,
                    reviewed_at="2026-09-30",
                    review_method="automated-test",
                    accept_only=True,
                )

            self.assertEqual(result, (1, 0, 1))
            papers = yaml.safe_load(papers_path.read_text(encoding="utf-8"))["papers"]
            rejected = yaml.safe_load(rejected_path.read_text(encoding="utf-8"))["rejected"]
            self.assertEqual(len(papers), 1)
            self.assertTrue(papers[0]["reviewed"])
            self.assertEqual(papers[0]["review_method"], "automated-test")
            self.assertEqual(rejected, [])
        finally:
            for path in paths:
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
