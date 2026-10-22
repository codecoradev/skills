# Contributing

Thanks for helping improve CodeCora agent skills.

## Layout

Each skill lives in `skills/<name>/SKILL.md`. The file starts with YAML frontmatter:

```yaml
---
name: my-skill        # lowercase letters, digits, hyphens; must equal the directory name
description: What it does and when an agent should use it.
---
```

Supporting files (references, scripts) go next to `SKILL.md` in the same directory.

## Workflow

1. Branch from `develop` (`feat/...`, `fix/...`, `docs/...`).
2. Run the linter: `python3 scripts/lint_skills.py` (and `--selftest` if you touched it).
3. Open a PR against `develop`. Use the PR template: `## What`, `## Why`, `## Testing`.
4. PRs are squash-merged. Use conventional commit titles (`feat:`, `fix:`, `docs:`, `chore:`).

## License

Contributions are licensed to the project under the Apache-2.0 license (inbound=outbound). No additional agreement is required.

## Rules

- English only.
- No credentials, tokens, personal emails, or machine-specific paths in committed files.
- Keep skills factual and tied to released behavior of the product they describe.
