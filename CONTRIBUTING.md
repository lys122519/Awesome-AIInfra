# Contributing

Thanks for helping maintain Awesome-AIInfra.

## Paper acceptance criteria

A paper should make a direct systems contribution to AI infrastructure, such as training, inference, serving, scheduling, communication, orchestration, accelerators, memory, storage, reliability, or benchmarking. Papers that merely apply an existing model to a domain are out of scope.

## Submission workflow

1. Search `data/papers.yaml` and `data/rejected.yaml` for duplicates.
2. Add accepted records to `data/papers.yaml`; do not edit the generated paper block in `README.md` directly.
3. Use one of the categories defined in `scripts/generate_readme.py`.
4. Prefer a DOI, publisher, OpenReview, or official conference URL for `publication`.
5. Add `code` only when it points to the authors' or project's repository.
6. Set `reviewed: true` and `reviewed_at` only after checking relevance, metadata, and category placement. Unreviewed candidates cannot pass validation.
7. Run:

   ```bash
   pip install -r requirements.txt
   python scripts/generate_readme.py
   python -m unittest discover -s tests -v
   ```

8. Commit both `data/papers.yaml` and the regenerated `README.md` in the same pull request.

Rejected tracker candidates should be added to `data/rejected.yaml` with a short reason.

For large tracker batches, `scripts/screen_candidates.py` can produce precision-oriented recommendations. These recommendations are not accepted records by themselves; review the decision file before setting `reviewed: true`.

After reviewing a decision file, apply it with:

```bash
python scripts/apply_screening.py path/to/screening-decisions.yaml --reviewed-at YYYY-MM-DD
python scripts/generate_readme.py
```

The importer is idempotent: records already present with the same decision are skipped, while conflicting decisions stop the import.
