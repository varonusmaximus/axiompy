# @!documentation

#!/usr/bin/env python3
"""
AI Code Review Script for GitHub Actions.

This script is designed to be used in a GitHub Actions workflow.
Copy this file to your repository at .github/scripts/code_review.py

Usage in GitHub Actions:
    - name: Run AI Code Review
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: python .github/scripts/code_review.py

Environment Variables:
    GITHUB_TOKEN: GitHub API token (provided by Actions)
    OPENAI_API_KEY: OpenAI API key (or ANTHROPIC_API_KEY)
    RULES_REPO: Central rules repository (optional, default: varonusmaximus/axiompy)
    GITHUB_REPOSITORY: Repository being reviewed (provided by Actions)
    GITHUB_REF: Git ref for the PR (provided by Actions)
"""

import os
import sys


def get_pr_info():
    """Extract PR information from GitHub Actions environment."""
    # Get repository
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        print("Error: GITHUB_REPOSITORY not set")
        sys.exit(1)

    owner, repo_name = repo.split("/")

    # Get PR number - try multiple methods
    pr_number = None

    # Method 1: Direct environment variable (for workflow_dispatch)
    if os.environ.get("PR_NUMBER"):
        pr_number = int(os.environ["PR_NUMBER"])

    # Method 2: GitHub event payload
    elif os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        # PR number is in GITHUB_REF_NAME for pull_request events
        ref = os.environ.get("GITHUB_REF", "")
        if "/pull/" in ref:
            pr_number = int(ref.split("/pull/")[1].split("/")[0])

    # Method 3: Parse from GITHUB_REF
    if not pr_number:
        ref = os.environ.get("GITHUB_REF", "")
        if "/pull/" in ref:
            pr_number = int(ref.split("/pull/")[1].split("/")[0])

    if not pr_number:
        print("Error: Could not determine PR number")
        print(f"  GITHUB_REF: {os.environ.get('GITHUB_REF', 'not set')}")
        print(f"  PR_NUMBER: {os.environ.get('PR_NUMBER', 'not set')}")
        sys.exit(1)

    return owner, repo_name, pr_number


def main():
    """Main entry point."""
    # Import here to fail fast if axiompy not installed
    try:
        from axiompy.agents import CodeReviewAgentFactory, ReviewSeverity
    except ImportError:
        print("Error: axiompy not installed")
        print("Run: pip install git+https://github.com/varonusmaximus/axiompy.git")
        sys.exit(1)

    # Get PR info
    owner, repo_name, pr_number = get_pr_info()
    rules_repo = os.environ.get("RULES_REPO", "varonusmaximus/axiompy")

    print("🔍 Starting AI Code Review")
    print(f"   Repository: {owner}/{repo_name}")
    print(f"   PR Number: #{pr_number}")
    print(f"   Rules Source: {rules_repo}")
    print()

    # Create agent
    try:
        agent = CodeReviewAgentFactory.create_from_env(rules_repo=rules_repo)
    except ValueError as e:
        print(f"Error creating agent: {e}")
        print()
        print("Required environment variables:")
        print("  GITHUB_TOKEN - GitHub API token")
        print("  OPENAI_API_KEY or ANTHROPIC_API_KEY - AI provider key")
        sys.exit(1)

    # Run review
    print("📋 Loading rules from AGENTS.md...")
    result = agent.review_pr(owner, repo_name, pr_number)

    # Print summary
    print()
    print("=" * 60)
    print("📊 REVIEW RESULTS")
    print("=" * 60)
    print(f"Score:           {result.score}/100")
    print(f"Rules Enforced:  {result.rules_enforced}")
    print(f"Total Comments:  {len(result.comments)}")
    print()

    # Count by severity
    critical = sum(1 for c in result.comments if c.severity == ReviewSeverity.CRITICAL)
    errors = sum(1 for c in result.comments if c.severity == ReviewSeverity.ERROR)
    warnings = sum(1 for c in result.comments if c.severity == ReviewSeverity.WARNING)
    info = sum(1 for c in result.comments if c.severity == ReviewSeverity.INFO)

    if critical > 0:
        print(f"🔴 Critical:     {critical}")
    if errors > 0:
        print(f"🟠 Errors:       {errors}")
    if warnings > 0:
        print(f"🟡 Warnings:     {warnings}")
    if info > 0:
        print(f"🔵 Info:         {info}")

    print()
    print(f"Approved:        {'✅ Yes' if result.approved else '❌ No'}")
    print(f"Review Event:    {result.review_event}")
    print("=" * 60)

    # Show top violations
    if result.violations_by_rule:
        print()
        print("📁 Top Violations:")
        for rule, count in sorted(result.violations_by_rule.items(), key=lambda x: -x[1])[:5]:
            print(f"   {rule}: {count}")

    print()

    # Exit code based on results
    if result.has_critical_issues:
        print("❌ FAILED: Critical issues found")
        print("   Please address critical issues before merging.")
        sys.exit(1)

    # Uncomment to also fail on errors:
    # if result.has_errors:
    #     print("⚠️ FAILED: Errors found")
    #     print("   Please address errors before merging.")
    #     sys.exit(1)

    print("✅ Review complete")
    print("   See PR comments for detailed feedback.")


if __name__ == "__main__":
    main()
