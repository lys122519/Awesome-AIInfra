import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_readme import (  # noqa: E402
    load_and_validate,
    load_and_validate_rejected,
    render_papers,
    validate_papers,
)
from screen_candidates import screen_candidate  # noqa: E402


class GenerateReadmeTests(unittest.TestCase):
    def test_repository_data_is_valid_and_renderable(self):
        papers = load_and_validate()
        load_and_validate_rejected(papers)
        rendered = render_papers(papers)
        self.assertEqual(rendered.count("[PUB]("), len(papers))

    def test_duplicate_publication_is_rejected(self):
        papers = [
                {
                    "title": f"Paper {index}",
                    "year": 2026,
                    "venue": "MLSys",
                    "category": "Training Systems",
                    "publication": "https://example.com/paper",
                    "source": "test",
                    "reviewed": True,
                    "reviewed_at": "2026-09-30",
                }
                for index in range(2)
            ]
        with self.assertRaisesRegex(ValueError, "duplicate publication URL"):
            validate_papers(papers)

    def test_screening_accepts_systems_work_and_rejects_ambiguous_inference(self):
        self.assertEqual(
            screen_candidate({"title": "Fast LLM Serving with KV Cache Scheduling", "venue": "ACL"})[0],
            "accept",
        )
        self.assertEqual(
            screen_candidate({"title": "An RDMA Storage Layer", "venue": "SOSP"})[0],
            "accept",
        )
        self.assertEqual(
            screen_candidate({"title": "A Generic Storage Layer", "venue": "SOSP"})[0],
            "reject",
        )
        self.assertEqual(
            screen_candidate({"title": "LLM Dataset Inference: Did You Train on My Data?", "venue": "ICML"})[0],
            "reject",
        )
        self.assertEqual(
            screen_candidate({"title": "LLMs for Medical Diagnosis", "venue": "EMNLP"})[0],
            "reject",
        )
        self.assertEqual(
            screen_candidate({"title": "A Benchmark for LLM Recommender Systems", "venue": "AAAI"})[0],
            "reject",
        )
        self.assertEqual(
            screen_candidate({"title": "GPU-Disaggregated Serving for Recommendation Models", "venue": "KDD"})[0],
            "accept",
        )


if __name__ == "__main__":
    unittest.main()
