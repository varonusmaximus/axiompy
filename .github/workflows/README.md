# GitHub Actions

Workflows for the **axiompy** repository (Python 3.10+ runtime; CI tests on **3.12**).

## Workflows

| File | When it runs | Purpose |
|------|----------------|----------|
| [`python-ci.yml`](python-ci.yml) | Push/PR to `main` or `develop`, or **manual** `workflow_dispatch` | **Ruff** (lint + format), **pytest + coverage** on **Python 3.12** (80% gate), **Bandit** + **pip-audit** (failing) |

There is **no** automated release or Artifactory publish workflow. Publish wheels/sdists from your machine (e.g. `poetry build` / `pip build`) or add a separate PyPI workflow later.

## Local checks (before push)

```bash
make lint
make test
make coverage
make security
```

Install hooks (optional):

```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
pre-commit run --all-files
```

## Secrets (CI)

| Secret | Used by | Notes |
|--------|---------|--------|
| `CODECOV_TOKEN` | Codecov upload step | Optional. Upload is non-blocking if unset. |

## Forks / personal repos

- CI installs dependencies from **PyPI** only (`pip install -e ".[...]"`).
- No Artifactory or private index is required for this workflow.

## References

- [GitHub Actions docs](https://docs.github.com/en/actions)
- [pytest](https://docs.pytest.org/)
- [Ruff](https://docs.astral.sh/ruff/)
- [pip-audit](https://pypi.org/project/pip-audit/)
