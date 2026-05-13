---
name: jira-workflow
description: Jira MCP workflow for creating, listing, updating, and closing issues. Use when the user asks to create a Jira issue, list project issues, update issue details, transition issue status, or close an issue.
---

# Jira MCP Workflow

## Create Issue

When the user asks to create a Jira issue, collect these before calling `create_issue`:

1. **Project Code** — e.g. `DAIENGEX` (optional if `JIRA_DEFAULT_PROJECT` is set)
2. **Summary** — Short title for the issue (required)
3. **Description** — Issue body/details (required)
4. **Component(s)** — One or more of: **Bug Fix**, **Discovery**, **Feature**, **Maintenance**, **Refactoring** (required for DAIENGEX)

Use `component_names` for components (e.g. `["Discovery"]`).

If the user omits any required field, ask for it.

## List / Select / Work

- **List all project issues** → `list_project_issues(project="DAIENGEX")`
- **List only issues assigned to me** → `list_project_issues(project="DAIENGEX", assigned_to_me=True)`
- **Put into work** → `get_transitions(issue_key)` then `transition_issue(issue_key, transition_id)` for "In Progress"
- **Update details** → `update_issue(issue_key, fields={"summary": "...", "description": "..."})`
- **Close** → `transition_issue(issue_key, transition_id)` for "Done"
