## What and why


## Checklist (docs/15-development-standards.md section 10)

- [ ] `python scripts/ci.py` is green (tests, black, ruff, mypy, bandit, pip-audit)
- [ ] New behaviour has tests and is traced to a requirement (docs/20)
- [ ] Documents, glossary and user manual match the behaviour
- [ ] New interface texts are translated (`test_i18n` passes) and went through the confidence check
- [ ] No colour outside the design tokens (`test_dark_mode`)
- [ ] A release PR only: `VERSION` and `pyproject.toml` raised, `python scripts/ci.py --pdf --showcase` run, `releases/v<version>/` committed
- [ ] No account, repository or personal names in documents (`test_no_account_names`)
