#!/usr/bin/env python3
"""Apply reviewed decisions or high-confidence automatic accepts."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import yaml

from generate_readme import (
    PAPERS_PATH,
    REJECTED_PATH,
    load_and_validate,
    load_and_validate_rejected,
    load_list,
    publication_key,
)


def apply_decisions(
    decision_path: Path,
    reviewed_at: str,
    review_method: str,
    accept_only: bool = False,
) -> tuple[int, int, int]:
    decisions = load_list(decision_path, "decisions")
    papers = load_and_validate(PAPERS_PATH)
    rejected = load_and_validate_rejected(papers, REJECTED_PATH)

    accepted_urls = {publication_key(item) for item in papers}
    rejected_urls = {publication_key(item) for item in rejected}

    added_accepted = 0
    added_rejected = 0
    skipped = 0
    for index, item in enumerate(decisions, start=1):
        publication = publication_key(item)
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
