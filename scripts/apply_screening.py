#!/usr/bin/env python3
"""Apply reviewed decisions or high-confidence automatic accepts."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PAPERS_PATH = ROOT / "data" / "papers.yaml"
REJECTED_PATH = ROOT / "data" / "rejected.yaml"


def _load_list(path: Path, key: str) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    values = payload.get(key, []) if isinstance(payload, dict) else []
    if not isinstance(values, list):
        raise ValueError(f"{path} must contain a top-level `{key}` list")
    return values


def _publication_key(record: dict) -> str:
    return str(record.get("publication", "")).strip().casefold()


def apply_decisions(
    decision_path: Path,
    reviewed_at: str,
    review_method: str,
    accept_only: bool = False,
) -> tuple[int, int, int]:
    decisions = _load_list(decision_path, "decisions")
    papers = _load_list(PAPERS_PATH, "papers")
    rejected = _load_list(REJECTED_PATH, "rejected")

    accepted_urls = {_publication_key(item) for item in papers}
    rejected_urls = {_publication_key(item) for item in rejected}
    if "" in accepted_urls | rejected_urls:
        raise ValueError("all accepted and rejected records must have a publication URL")
    overlap = accepted_urls & rejected_urls
    if overlap:
        raise ValueError(f"accepted/rejected datasets already overlap: {sorted(overlap)[0]}")

    added_accepted = 0
    added_rejected = 0
    skipped = 0
    for index, item in enumerate(decisions, start=1):
        publication = _publication_key(item)
        decision = item.get("decision")
        if not publication:
            raise ValueError(f"decision #{index} has no publication URL")
        if decision not in {"accept", "reject"}:
            raise ValueError(f"decision #{index} has an invalid decision: {decision!r}")
        if accept_only and decision != "accept":
            skipped += 1
            continue

        if publication in accepted_urls:
            if decision != "accept":
                raise ValueError(f"existing accepted paper was rejected: {item['publication']}")
            skipped += 1
            continue
        if publication in rejected_urls:
            if decision != "reject":
                raise ValueError(f"existing rejected paper was accepted: {item['publication']}")
            skipped += 1
            continue

        if decision == "accept":
            paper = {
                key: value
                for key, value in item.items()
                if key not in {"decision", "reason", "reviewed"}
            }
            paper.update(
                reviewed=True,
                reviewed_at=reviewed_at,
                review_method=review_method,
                screening_reason=item["reason"],
            )
            papers.append(paper)
            accepted_urls.add(publication)
            added_accepted += 1
        else:
            rejection = {
                key: item[key]
                for key in ("title", "year", "venue", "publication", "source")
                if item.get(key) not in (None, "")
            }
            rejection.update(
                reason=item["reason"],
                reviewed_at=reviewed_at,
                review_method=review_method,
            )
            rejected.append(rejection)
            rejected_urls.add(publication)
            added_rejected += 1

    PAPERS_PATH.write_text(
        yaml.safe_dump({"papers": papers}, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    REJECTED_PATH.write_text(
        "# Candidates rejected during review are recorded here to avoid repeated work.\n"
        + yaml.safe_dump({"rejected": rejected}, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    return added_accepted, added_rejected, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decisions", type=Path, help="reviewed YAML produced by screen_candidates.py")
    parser.add_argument("--reviewed-at", default=date.today().isoformat())
    parser.add_argument("--review-method", default="ai-infra-title-policy-v1")
    parser.add_argument(
        "--accept-only",
        action="store_true",
        help="Apply high-confidence accept decisions and leave all rejects unrecorded",
    )
    args = parser.parse_args()
    accepted, rejected, skipped = apply_decisions(
        args.decisions, args.reviewed_at, args.review_method, args.accept_only
    )
    print(f"Added {accepted} accepted and {rejected} rejected records; skipped {skipped} existing records.")


if __name__ == "__main__":
    main()
