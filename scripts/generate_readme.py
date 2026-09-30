#!/usr/bin/env python3
"""Validate data/papers.yaml and generate the curated README paper list."""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PAPERS_PATH = ROOT / "data" / "papers.yaml"
REJECTED_PATH = ROOT / "data" / "rejected.yaml"
TEMPLATE_PATH = ROOT / "README.template.md"
README_PATH = ROOT / "README.md"

CATEGORY_ORDER = [
    "Training Systems",
    "Inference and Serving",
    "Scheduling and Resource Management",
    "Distributed Communication and Networking",
    "Cloud and Kubernetes",
    "Accelerators, Architecture and Memory",
    "Storage and Data Pipelines",
    "Observability, Reliability and Benchmarking",
    "Efficient LLM Systems",
]

REQUIRED_FIELDS = {
    "title",
    "year",
    "venue",
    "category",
    "publication",
    "source",
    "reviewed_at",
}


def validate_papers(papers: object) -> list[dict]:
    if not isinstance(papers, list):
        raise ValueError("data/papers.yaml must contain a top-level `papers` list")

    seen_titles: set[str] = set()
    seen_publications: set[str] = set()
    for index, paper in enumerate(papers, start=1):
        if not isinstance(paper, dict):
            raise ValueError(f"paper #{index} must be a mapping")
        missing = sorted(field for field in REQUIRED_FIELDS if not paper.get(field))
        if missing:
            raise ValueError(f"paper #{index} is missing: {', '.join(missing)}")
        if paper.get("reviewed") is not True:
            raise ValueError(f"paper #{index} must have reviewed: true")
        if paper["category"] not in CATEGORY_ORDER:
            raise ValueError(f"paper #{index} has unknown category: {paper['category']}")
        try:
            paper["year"] = int(paper["year"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"paper #{index} has an invalid year") from exc

        title_key = " ".join(str(paper["title"]).casefold().split())
        publication_key = str(paper["publication"]).strip().casefold()
        if title_key in seen_titles:
            raise ValueError(f"duplicate title: {paper['title']}")
        if publication_key in seen_publications:
            raise ValueError(f"duplicate publication URL: {paper['publication']}")
        seen_titles.add(title_key)
        seen_publications.add(publication_key)
    return papers


def load_and_validate(path: Path = PAPERS_PATH) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    papers = payload.get("papers", []) if isinstance(payload, dict) else []
    return validate_papers(papers)


def load_and_validate_rejected(
    accepted_papers: list[dict], path: Path = REJECTED_PATH
) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rejected = payload.get("rejected", []) if isinstance(payload, dict) else []
    if not isinstance(rejected, list):
        raise ValueError("data/rejected.yaml must contain a top-level `rejected` list")

    accepted_urls = {str(paper["publication"]).strip().casefold() for paper in accepted_papers}
    seen_urls: set[str] = set()
    required = {"title", "publication", "reason", "source", "reviewed_at"}
    for index, record in enumerate(rejected, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"rejected record #{index} must be a mapping")
        missing = sorted(field for field in required if not record.get(field))
        if missing:
            raise ValueError(f"rejected record #{index} is missing: {', '.join(missing)}")
        publication = str(record["publication"]).strip().casefold()
        if publication in accepted_urls:
            raise ValueError(f"publication is both accepted and rejected: {record['publication']}")
        if publication in seen_urls:
            raise ValueError(f"duplicate rejected publication URL: {record['publication']}")
        seen_urls.add(publication)
    return rejected


def _venue_year_anchor(venue: str, year: int) -> str:
    venue_slug = re.sub(r"[^a-z0-9]+", "-", venue.casefold()).strip("-")
    return f"{venue_slug}-{year}"


def render_papers(papers: list[dict]) -> str:
    grouped: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for paper in papers:
        grouped[str(paper["venue"])][paper["year"]].append(paper)

    venues = sorted(grouped, key=str.casefold)
    lines = ["### Quick Links by Venue and Year", ""]
    for venue in venues:
        links = [
            f"[{venue} {year}](#{_venue_year_anchor(venue, year)})"
            for year in sorted(grouped[venue], reverse=True)
        ]
        lines.append("- " + " · ".join(links))

    lines.append("")
    for venue in venues:
        lines.extend([f"### {venue}", ""])
        for year in sorted(grouped[venue], reverse=True):
            lines.extend(
                [
                    f'<a id="{_venue_year_anchor(venue, year)}"></a>',
                    f"#### {year}",
                    "",
                ]
            )
            year_papers = sorted(
                grouped[venue][year],
                key=lambda item: str(item["title"]).casefold(),
            )
            for paper in year_papers:
                links = [f"[PUB]({paper['publication']})"]
                if paper.get("code"):
                    links.append(f"[CODE]({paper['code']})")
                lines.append(
                    f"- **{paper['title']}** — {paper['category']}. " + " ".join(links)
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_readme(papers: list[dict]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    start = "<!-- PAPERS:START -->"
    end = "<!-- PAPERS:END -->"
    if start not in template or end not in template:
        raise ValueError("README.template.md is missing the generated block markers")
    before, remainder = template.split(start, 1)
    _, after = remainder.split(end, 1)
    generated = (
        f"{start}\n"
        "<!-- Generated by scripts/generate_readme.py. Do not edit this block manually. -->\n\n"
        f"{render_papers(papers)}\n"
        f"{end}"
    )
    return before + generated + after


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if README.md is not current")
    args = parser.parse_args()

    papers = load_and_validate()
    rejected = load_and_validate_rejected(papers)
    expected = build_readme(papers)
    if args.check:
        actual = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""
        if actual != expected:
            print("README.md is out of date; run python scripts/generate_readme.py", file=sys.stderr)
            return 1
        print(
            f"Validated {len(papers)} accepted and {len(rejected)} rejected records; "
            "README.md is current."
        )
        return 0

    README_PATH.write_text(expected, encoding="utf-8")
    print(
        f"Validated {len(papers)} accepted and {len(rejected)} rejected records "
        f"and regenerated {README_PATH.name}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
