# Agent Guidance for Awesome-AIInfra

Awesome-AIInfra is the curated knowledge base paired with [AIInfra-paper-update-tracker](https://github.com/lys122519/AIInfra-paper-update-tracker). The tracker discovers candidates; this repository accepts human-reviewed records and high-confidence records admitted by the automatic policy.

[CONTRIBUTING.md](CONTRIBUTING.md) is the single source for data files, acceptance criteria, validation commands, screening, and automatic curation. Follow it.

Constraints that are easy to violate:

- Never edit the generated paper block in `README.md`; change `data/papers.yaml` or `README.template.md` and run `python scripts/generate_readme.py`.
- The generated block is grouped by venue and year: venues and titles are alphabetized, years are newest-first, and quick links use stable explicit venue-year anchors.
- Never record automatic rejects, and never import an entire tracker cache.
