# Working in this repository

The CSCM Tool (Controller Status Code Management Tool) is developed trunk-based: `main` is always releasable, work happens on short-lived branches, and nothing reaches `main` without a green pipeline and a review by the Software Owner.

## First time

```bash
git clone <address of this repository> cscm
python cscm/cscm_tool/scripts/first_start.py
```

[DEPLOYMENT-QUICKSTART.md](DEPLOYMENT-QUICKSTART.md) explains every step and the usual error messages.

## A change

1. Branch from `main`: `feature/<topic>`, `fix/<topic>` or `docs/<topic>`.
2. Change code, tests and documents together. Every new behaviour is traced to a requirement in `docs/03-srs.md` and `docs/20-traceability-matrix.md`.
3. Run `python scripts/ci.py` inside `cscm_tool` (about 20 minutes). It must be green.
4. Open a pull request; the checklist is in the template. The pipeline (`verify`, `deploy-scripts`) and a review by the code owner are required.
5. Squash-merge. The commit message starts with what changed, and with the version when it is a release.

## A release

1. Raise `VERSION` in `cscm_tool/app/version.py` and `version` in `cscm_tool/pyproject.toml` (a test keeps them equal).
2. Run `python scripts/ci.py --pdf --showcase`: the pipeline, then the four PDFs and the two design decks (each as `.pptx` and `.pdf`) in `releases/v<version>/`. Commit them.
3. Merge, then tag `v<version>` on `main` (annotated) and publish a release with the files of `releases/v<version>/` attached.

## Rules that are tested

- No colour outside the design tokens, and a dark value for every token (`test_dark_mode`).
- Every text goes through `_()` and is translated; new words go through the confidence check.
- No account, repository or personal names in documents and scripts (`test_no_account_names`); who owns the software is written once in `cscm_tool/app/branding.py`.
- No data, keys or `.env` files in the repository.

See [docs/15-development-standards.md](docs/15-development-standards.md) for the full standards.
