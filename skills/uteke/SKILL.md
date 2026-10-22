---
name: uteke
description: Use the Uteke offline semantic memory engine (single Rust binary, no API keys) to store, recall and maintain persistent memories and docs across agent sessions.
---

# Uteke — persistent semantic memory for agents

Uteke is an offline-first, local-first semantic memory engine shipped as one Rust binary (Apache-2.0). Core operation needs no API keys. Data lives in `~/.codecora/uteke/` (SQLite + vector index). Commands below were verified against `uteke` v0.21.1 `--help`; run `uteke <cmd> --help` if your version differs.

## When to Use

- You need facts, decisions, preferences or procedures to survive between sessions.
- Several agents share one knowledge base (fleet, rooms, tags, author).
- Work must stay offline/private (no data leaves the machine in the default setup).
- Do NOT use it as a scratchpad for transient chat state; store only what a future session should know.

## Install and setup

```bash
# Linux x86_64 (aarch64, macOS, Windows assets also exist on the releases page)
mkdir -p /tmp/uteke-dl && curl -fsSL -L https://github.com/codecoradev/uteke/releases/latest/download/uteke-x86_64-unknown-linux-gnu.tar.gz | tar xz -C /tmp/uteke-dl
install -m 755 /tmp/uteke-dl/uteke ~/.local/bin/uteke   # ensure ~/.local/bin is on PATH
uteke --version && uteke doctor     # health: DB, index, model, consistency
uteke upgrade                       # self-update later (-y skips the prompt)
```

Wire it into an agent: `uteke init --agent pi|claude|cursor|opencode|hermes` (default `pi`).
For Hermes, add `--memory-provider` to install automatic recall + extraction as the default memory instead of the manual tool plugin.
`uteke guide` prints an agent-facing tools guide suitable for system-prompt injection.

Server mode (shared/remote): binaries `uteke-serve` and `uteke-mcp`, or Docker `ghcr.io/codecoradev/uteke:latest`. Clients read env vars `UTEKE_BASE_URL` (default `http://localhost:8767`), `UTEKE_TOKEN`, `UTEKE_NAMESPACE`.

## Core loop

```bash
# 1. Recall BEFORE answering/starting work (unified: memories + docs)
uteke recall "how do we deploy the api" --limit 5
uteke recall "deploy" --context            # formatted for prompt injection
uteke recall "deploy" --pack --budget 4000 # budgeted pack; --exclude-ids a,b to skip already-injected

# 2. Remember durable knowledge
uteke remember "Deploys go through GitHub Actions, never manual scp" \
  --type procedure --tags deploy,ci --source "docs/deploy.md"

# 3. Maintain
uteke get <id>
uteke update <id> --content "..." --tags a,b --importance 0.8 --pinned true --type decision
uteke forget <id>
```

Verified `remember` options: `--tags` (comma-separated), `--type` (fact, procedure, preference, decision, context, note, insight, reference, event; default `fact` auto-infers the type), `--entity`, `--category`, `--meta k:v,k:v`, `--room`, `--author`, `--author-type human|agent`, `--source`, `--source-type`, `--timestamp`, `--detect-contradiction`. There is no `--importance` on `remember`; set importance afterwards with `update --importance`.

Recall tuning (all verified): `--tags`, `--type all|memory|doc`, `--entity`, `--category`, `--min <0-1>`, `--strict`, `--strategy vector|fts5|hybrid|graph|fusion` (default fusion), `--explain`, `--related --depth N`, `--at <RFC3339>` (time travel), `--enrich`, `--json`.
Use `uteke search "<keywords>"` for plain keyword matching and `uteke list --tag x --limit N --offset M` to browse.

Writing good memories:
- One atomic fact per memory; self-contained (no "as above"); include the why.
- Pick `--type` explicitly for decisions and procedures instead of relying on inference.
- When knowledge changes: `update <id>` for corrections; `uteke supersede <old> <new>` when a new memory replaces a stale one; `remember --detect-contradiction` to auto-deprecate conflicts.
- `uteke pin <id>` for must-never-decay facts; `uteke feedback` records usefulness of a memory.
- Never store secrets or tokens.

## Memory hygiene (when to run which)

| Situation | Command |
|---|---|
| Quick overview | `uteke stats`, `uteke context` |
| Something feels broken | `uteke doctor`, then `uteke verify` (DB vs index consistency) |
| Binary integrity | `uteke verify-checksums` |
| Index corrupt / memories not found | `uteke repair`; if it fails `repair --rebuild`; missing vectors `repair --reembed` |
| See what is stale | `uteke aging status`, `aging preview` (dry run), `aging cleanup` (`--yes` skips prompt) |
| TTL-based cleanup | `uteke prune --ttl 30 --dry-run` first, then without `--dry-run` |
| Soft-deprecate/auto-prune cycle | `uteke lifecycle status`, `lifecycle cycle`; undo with `lifecycle promote <id>` |
| Near-duplicates | `uteke consolidate --threshold 0.90 --dry-run`, then run for real |
| Full maintenance pass | `uteke dream --dry-run` (lint → backlinks → dedup → orphans → compact → verify) |
| Backup / migrate | `uteke export backup.jsonl` (no embeddings); `export --full` round-trips rooms, graph, docs; `uteke import file --format auto|jsonl|markdown|text --tags x` (re-embeds) |

Rules of thumb: always dry-run destructive commands (`prune`, `consolidate`, `aging cleanup`, `dream`) first; `forget --all` and bulk forgets (`--tag`, `--cold`) are destructive and need `--confirm` in scripts; export before bulk cleanup. `import --extract` distills input into atomic facts (offline rule-based by default).
Tag housekeeping: `uteke tags list|rename|delete`.

## Rooms, tags, namespaces (multi-agent)

- `--namespace` is marked DEPRECATED in v0.21.1 help ("namespaces will be removed in a future 0.x release; prefer rooms, tags and author"). Writing to a non-default namespace prints a warning. Default to the `default` namespace.
- Shared context: `uteke room create|list|stats|recall|summary`, and `remember --room <id> --author <agent>`. `room recall` reads a room across namespaces.
- Tag convention (suggested): `project:<name>`, `agent:<name>`, topic tags (`deploy`, `auth`), and one lifecycle tag (`wip`, `decided`). Keep a small vocabulary; audit with `tags list` and merge with `tags rename`.
- Use `--author` / `--author-type` so humans and agents are distinguishable.

## Docs layer vs memories

- Memories: short, atomic, decay/age, ranked by importance and recency. Use for facts, decisions, preferences.
- Docs (`uteke doc`): long-form wiki pages addressed by slug, optionally hierarchical. Use for runbooks, specs, architecture notes.
- `uteke recall` searches both by default (`--type memory|doc` to narrow); `uteke doc search "<q>"` searches docs only.

```bash
uteke doc create runbooks/deploy --title "Deploy runbook" --file deploy.md --tags ops --parent runbooks
uteke doc get runbooks/deploy
uteke doc list | children | descendants | breadcrumbs | move | update | delete | export
```

`doc create` creates or updates by slug (content via `--file`, `--file -` for stdin, or `--content`). `doc delete` cascades to children. Docs are global in this deployment's convention (not namespaced).

## Auto-context hook and agent init

- `uteke hook bash|zsh|fish` prints a shell script for auto-context loading: `eval "$(uteke hook bash)"` in `~/.bashrc`.
- `uteke init --agent <agent>` installs the integration for that agent; run it once per agent and re-run after `uteke upgrade`.
- Session pattern: start with `uteke context` + `uteke recall "<task>" --context`; end by `remember`-ing decisions and lessons.

## Pitfalls

- GitHub release assets redirect: use `curl -fsSL -L` (follow redirects) or you may save an HTML/redirect body and `tar` fails.
- Extract the tarball into a fresh empty directory (`tar xz -C <dir>`): extracting into a dir already containing a `uteke` file or in-use binary can fail with a "file exists"/"text file busy" error. Prefer `uteke upgrade` once installed.
- `remember` has no `--importance`; use `update --importance` (0.0–1.0).
- `update --tags` replaces the whole tag set, not appends.
- Default `--type fact` triggers auto-inference; pass `--type` explicitly when it matters.
- `recall --limit` defaults to 5; raise it or use `--pack` for broader context.
- Memories missing embeddings are invisible to semantic recall until `repair --reembed`.
- Env-specific: when run through agent sandboxes with command allowlists, chains like `cd x && uteke ...` may not match the allowlist; call `uteke` directly with `--store` if needed.
