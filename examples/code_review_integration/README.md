# Code Review Agent Integration Guide

This guide shows how another team can integrate the axiompy Code Review Agent into their repository.

## Quick Start (5 Minutes)

### Step 1: Add GitHub Action

Create `.github/workflows/ai-code-review.yml` in your repository:

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install axiompy
        run: pip install git+https://github.com/varonusmaximus/axiompy.git

      - name: Run AI Code Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: python .github/scripts/code_review.py
```

### Step 2: Add Review Script

Create `.github/scripts/code_review.py`:

```python
#!/usr/bin/env python3
"""AI Code Review Script for GitHub Actions."""

import os
import sys

from axiompy.agents import CodeReviewAgentFactory

def main():
    # Get PR info from GitHub Actions environment
    pr_number = int(os.environ.get("GITHUB_PR_NUMBER", os.environ.get("PR_NUMBER", "0")))
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not pr_number or not repo:
        # Try to parse from GITHUB_REF
        ref = os.environ.get("GITHUB_REF", "")
        if "/pull/" in ref:
            pr_number = int(ref.split("/pull/")[1].split("/")[0])
        repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not pr_number:
        print("Could not determine PR number")
        sys.exit(1)

    owner, repo_name = repo.split("/")

    print(f"🔍 Reviewing PR #{pr_number} in {owner}/{repo_name}")

    # Create agent - uses GITHUB_TOKEN and OPENAI_API_KEY from env
    agent = CodeReviewAgentFactory.create_from_env(
        rules_repo="varonusmaximus/axiompy"  # Central rules repository
    )

    # Run review
    result = agent.review_pr(owner, repo_name, pr_number)

    # Print results
    print(f"\n{'='*60}")
    print(f"Score: {result.score}/100")
    print(f"Rules enforced: {result.rules_enforced}")
    print(f"Comments: {len(result.comments)}")
    print(f"Approved: {result.approved}")
    print(f"{'='*60}\n")

    # Exit with error if critical issues
    if result.has_critical_issues:
        print("❌ FAILED: Critical issues found")
        sys.exit(1)

    # Optionally fail on errors too
    # if result.has_errors:
    #     print("⚠️ FAILED: Errors found")
    #     sys.exit(1)

    print("✅ Review complete")

if __name__ == "__main__":
    main()
```

### Step 3: Add Secrets

In your GitHub repository settings, add:

| Secret | Value |
|--------|-------|
| `OPENAI_API_KEY` | Your OpenAI API key (`sk-...`) |

> **Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### Step 4: (Optional) Local Rule Overrides

Create `.cursorrules` in your repo root to override or disable specific rules:

```markdown
# Local Rule Overrides

## Overrides

### Factory Pattern (WARNING)
This legacy repo is gradually adopting factories.

## Disabled Rules
- magic_numbers
- primitive_obsession
```

## That's It! 🎉

The next time a PR is opened, the agent will:
1. Fetch your **rules file** (for example root **`AGENTS.md`** — today a short stub — or any markdown you maintain) from your central axiompy repository
2. Merge with any local `.cursorrules` overrides
3. Review the PR changes against all rules
4. Post inline comments on violations
5. Approve, request changes, or comment based on severity

---

## Advanced Configuration

### Custom Settings

For more control, modify the review script:

```python
from axiompy.agents import CodeReviewAgentFactory, CodeReviewSettings
from axiompy.reasoning import ReasoningProvider

settings = CodeReviewSettings(
    # Rules source
    rules_repo="varonusmaximus/axiompy",
    rules_file="AGENTS.md",
    rules_branch="main",

    # File filters
    include_patterns=["*.py"],  # Only Python files
    exclude_patterns=[
        "tests/*",
        "migrations/*",
        "*.generated.py",
    ],

    # Behavior
    large_pr_warning_threshold=30,
    very_large_pr_warning_threshold=100,
    post_review_to_github=True,
    fail_on_critical=True,
    fail_on_error=False,

    # AI settings
    temperature=0.2,
    max_tokens=2000,
)

agent = CodeReviewAgentFactory.create(
    github_token=os.environ["GITHUB_TOKEN"],
    ai_provider=ReasoningProvider.OPENAI,
    api_key=os.environ["OPENAI_API_KEY"],
    model="gpt-4o",
    settings=settings,
)
```

### Using Anthropic Instead

```python
agent = CodeReviewAgentFactory.create(
    github_token=os.environ["GITHUB_TOKEN"],
    ai_provider=ReasoningProvider.ANTHROPIC,
    api_key=os.environ["ANTHROPIC_API_KEY"],
    model="claude-sonnet-4-20250514",
    rules_repo="varonusmaximus/axiompy",
)
```

### Using Ollama (Self-Hosted)

```python
agent = CodeReviewAgentFactory.create(
    github_token=os.environ["GITHUB_TOKEN"],
    ai_provider=ReasoningProvider.OLLAMA,
    model="codellama",
    rules_repo="varonusmaximus/axiompy",
)
```

> **Note**: Ollama requires a self-hosted runner with Ollama installed.

### Reusable Workflow

For organization-wide deployment, create a reusable workflow:

**In `your-org/workflows` repo:**

```yaml
# .github/workflows/reusable-code-review.yml
name: Reusable AI Code Review

on:
  workflow_call:
    inputs:
      rules_repo:
        type: string
        default: 'varonusmaximus/axiompy'
      python_version:
        type: string
        default: '3.11'
    secrets:
      OPENAI_API_KEY:
        required: true

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python_version }}

      - run: pip install git+https://github.com/varonusmaximus/axiompy.git

      - name: Review PR
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          RULES_REPO: ${{ inputs.rules_repo }}
        run: |
          python -c "
          import os
          from axiompy.agents import CodeReviewAgentFactory

          agent = CodeReviewAgentFactory.create_from_env(
              rules_repo=os.environ.get('RULES_REPO')
          )

          # Parse GitHub context
          ref = os.environ.get('GITHUB_REF', '')
          pr_number = int(ref.split('/pull/')[1].split('/')[0]) if '/pull/' in ref else 0
          owner, repo = os.environ['GITHUB_REPOSITORY'].split('/')

          result = agent.review_pr(owner, repo, pr_number)

          print(f'Score: {result.score}/100')
          exit(1 if result.has_critical_issues else 0)
          "
```

**In each repo that wants code review:**

```yaml
# .github/workflows/code-review.yml
name: Code Review

on:
  pull_request:

jobs:
  review:
    uses: your-org/workflows/.github/workflows/reusable-code-review.yml@main
    secrets:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## Troubleshooting

### "GITHUB_TOKEN environment variable required"

Make sure your workflow has:
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### "OpenAI API key required"

Add `OPENAI_API_KEY` to your repository secrets.

### Review not posting comments

Check that your workflow has permissions:
```yaml
permissions:
  pull-requests: write
  contents: read
```

### Rules not loading from central repo

1. Verify `rules_repo` is correct (format: `owner/repo`)
2. Check that the configured `rules_file` (often `AGENTS.md`) exists in the specified branch
3. Ensure the GitHub token has read access to the rules repo

### Review taking too long

- Large PRs with many files take longer
- Consider using `gpt-4o-mini` for faster reviews
- Reduce `max_tokens` in settings

---

## Support

- **Issues**: [github.com/varonusmaximus/axiompy/issues](https://github.com/varonusmaximus/axiompy/issues)
- **Documentation**: [axiompy/agents/README.md](../../../axiompy/agents/README.md)
- **Examples**: This directory
