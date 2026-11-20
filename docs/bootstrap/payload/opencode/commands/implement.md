---
description: Implement one approved ready-for-agent GitHub ticket using Matt Pocock's implement workflow
agent: implementer
---

Read `AGENTS.md`, `docs/agents/project-state.md` and `docs/agents/opencode.md`, then load the `implement` skill.

Implement exactly the GitHub implementation ticket identified by `$ARGUMENTS`.

The target must be an approved `ready-for-agent` implementation ticket produced from the parent spec, not a Wayfinder decision ticket or broad spec issue. Read the ticket, its comments, its parent spec, `GLOSSARY.md`, and all relevant ADRs before editing code.

Work only in the current isolated ticket branch/worktree. Follow the agreed test seam, TDD and code-review workflow, and verify every acceptance criterion before completion. Do not broaden scope or invent product/architecture decisions that are absent from the source artifacts.

Do not deploy, mutate production resources/secrets, publish packages, merge, or push changes. Leave file changes to the trusted harness for commit/publication, then report the verified result.

The trusted harness supplies GitHub ticket, PR and review context without exposing a GitHub token. Read that supplied context instead of invoking gh. Run no browser. Reviewer reports are published by the workflow with their exact HEAD marker; no worker publishes directly.
