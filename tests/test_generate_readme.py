import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_readme import load_and_validate, render_papers, validate_papers  # noqa: E402


class GenerateReadmeTests(unittest.TestCase):
    def test_repository_data_is_valid_and_renderable(self):
        papers = load_and_validate()
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


if __name__ == "__main__":
    unittest.main()
