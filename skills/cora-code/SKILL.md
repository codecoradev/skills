---
name: cora-code
description: Use the Cora Code CLI (`cora`) to review diffs before commit or merge, run security scans, and understand or query a codebase (index, brain search, call tracing); use it when you need a BYOK AI code review, a static scan, or code intelligence.
---

# Cora Code (`cora`)

Cora Code is an AI-powered code review and code intelligence CLI (Rust binary `cora`, crate `cora-code`). Bring your own LLM API key (any OpenAI-compatible endpoint). Tagline: "Understand your code, deeply."

It is **not** an AI coding agent (it never writes code) and **not** a language server. It reviews diffs, scans projects, and answers structural questions about a codebase. Verified against `cora` v0.19.0 — run `cora <subcommand> --help` if a flag differs on your version.

## When to Use

- Pre-commit review of staged changes.
- PR / branch review against a base ref.
- Security / static scan of a project (works without an LLM key via `--no-llm`).
- Understanding an unfamiliar codebase: symbol search, callers, impact, call-path tracing.
- CI gate on pull requests (see CI integration).

Do not use it to generate or edit code.

## Install and BYOK setup

Install the binary from GitHub Releases (github.com/codecoradev/cora-code/releases), e.g. `cora-x86_64-unknown-linux-gnu.tar.gz`; aarch64, macOS and Windows assets also exist. Update later with `cora upgrade`.

```bash
cora init                      # creates .cora.yaml and installs the pre-commit hook (--no-hook to skip, --force to overwrite)
cora config set provider openai
cora config set model gpt-4o-mini
cora config set base_url https://api.openai.com/v1   # any OpenAI-compatible endpoint
cora auth login                # store API key locally (or set CORA_API_KEY, e.g. in CI)
cora auth status               # confirm a key is configured
cora config validate           # check resolved config
cora providers                 # list detected LLM providers
```

`cora config set` accepts keys: model, provider, base_url, format, severity. Config can also come from `.cora.yaml`, flags, or env vars (`CORA_PROVIDER`, `CORA_MODEL`, `CORA_BASE_URL`, `CORA_API_KEY`, `CORA_FORMAT`).

Never paste an API key into a committed file; use `cora auth login` or `CORA_API_KEY`.

## Review modes

`cora review` needs an LLM key. Without a key, or with `--no-llm`, only deterministic checks run.

| Flag | Reviews | Typical use |
|------|---------|-------------|
| `--staged` | `git diff --cached` | Pre-commit (pair with `cora hook install`) |
| `--unstaged` | working tree changes | Quick check while editing |
| `--base <ref>` | changes vs a base branch | Branch / PR review, e.g. `--base develop` |
| `--unpushed` | HEAD vs `@{u}` | Before `git push` |
| `--commit <ref>` | a commit or range (`HEAD`, `HEAD~3..HEAD`) | Review past commits |
| `--diff-file <path>` | a diff read from a file | Diffs from outside git |

Useful modifiers: `--format pretty|json|compact|sarif`, `--severity info|minor|major|critical` (minimum severity), `--output-file <path>`, `-q/--quiet`, `--no-cache`, `--stream`, `--max-diff-size <chars>` (default 50000; large diffs are auto-chunked unless `--no-auto-chunk`), `--ci`.

```bash
cora hook install                                  # pre-commit hook (uninstall: cora hook uninstall)
cora review --staged --format compact              # what the pre-commit pipeline runs
cora review --base develop --severity major        # branch review, majors and up
cora review --ci --format sarif --output-file cora.sarif
```

`--ci` skips the diff size limit and **exits 2 if there are any findings**. `--upload` uploads SARIF to GitHub Code Scanning (implies `--format sarif`; uses `GITHUB_TOKEN`).

### Reading the verdict

A clean review ends with the line `No issues found.` Anything else is a findings list with severities (info, minor, major, critical). Fix or consciously dismiss every finding before committing. Match on the `No issues found.` marker rather than on the exit code alone when scripting.

`cora commit` reviews staged changes, generates a commit message, and commits (`--no-review`, `--edit`, `--force`, `--yolo`). Avoid `--yolo` and `--force` in agent sessions: they skip prompts and the quality gate.

## Static analysis: `cora scan`

`cora scan` scans a directory (not a diff) for issues. Only deterministic checks run with no key or with `--no-llm`; with a key, LLM analysis is added. It targets security issues and secret patterns; run `cora scan --no-llm` on a sample to see which rules fire.

```bash
cora scan --no-llm                         # deterministic only, no key needed
cora scan --path services/api --exclude "vendor/**" --format json
cora scan --incremental                    # only files changed since last scan
cora scan --focus <area>                   # override focus areas from config
```

Scan vs review: **scan** looks at the whole tree (secrets, security rules, audits); **review** looks at what changed and judges intent and logic. They complement each other; run scan on a new repo or periodically, review on every change. For lower-level rule inspection see `cora profile` (quality profile presets).

## Code intelligence

Build the symbol index first, then query it.

```bash
cora index                 # build/update index (--rebuild, --prune, --stats, --watch)
cora explore <query>       # search the symbol index
cora brain <query...>      # hybrid search: FTS5 + vector + graph, RRF fusion (--limit, --json)
cora callers <symbol>      # who calls this?
cora impact <symbol>       # what breaks if I change it? (--depth, default 3)
cora trace <symbol>        # execution paths; --direction outgoing|incoming, --depth N
cora arch                  # modules, edge types, structure
cora routes                # detected HTTP routes (Axum, Actix, Express, FastAPI, Flask, Go)
cora dead-code             # functions/methods with no callers
cora affected              # tests affected by changed files
cora query "main -> *"     # simple graph patterns, e.g. "* -> authenticate"
```

Recipe — understand an unfamiliar codebase:

1. `cora index` then `cora index --stats` to confirm it built.
2. `cora arch` for the module layout; `cora routes` if it is a web service.
3. `cora brain "how are requests authenticated"` to find entry points.
4. `cora trace <symbol> --depth 3` for outgoing calls; `--direction incoming` for callers.
5. Before changing a symbol: `cora impact <symbol>` and `cora affected` to pick tests.

Add `--json` for machine-readable output. `cora watch` (or `cora index --watch`) keeps the index fresh.

## Findings workflow

Review results are stored and tracked per project.

```bash
cora findings list [--all] [--severity major] [--file <substr>] [--limit N] [--json]
cora findings stats
cora findings dismiss <ID> --reason "false positive: validated upstream"
cora findings reopen <ID>
cora debt [--trend] [--estimate] [--since YYYY-MM-DD|tag] [--branch <name>]
```

`list` shows open findings by default. Dismiss only with a real reason; it marks the finding won't-fix.

## CI integration

Official GitHub Action: `codecoradev/cora-review-action`. Pattern: the review runs on each PR and posts its verdict as a PR comment. **The comment is the gate**: check it for the `No issues found.` marker; a green check status alone is not sufficient evidence the review passed. See the action's README for inputs. For custom CI, use `cora review --ci --base <ref>` (exit 2 on findings) with `CORA_API_KEY` from secrets, optionally `--upload` for Code Scanning.

## Agent integration (MCP)

`cora mcp` starts an MCP server (`cora serve` does the same with auto-reindex on startup). It exposes code-intelligence tools plus agent-as-reviewer tools (`cora.review_prepare`/`review_finalize`, `cora.scan_prepare`/`scan_finalize`) where the calling agent does the judging with its own model, so no API key is needed in cora. Results from this path are advisory, not a CI gate.

```bash
cora install --list        # detect supported agents
cora install -y            # configure all detected (--agents cline,cursor; --dry-run; --remove)
claude mcp add cora -- cora mcp    # Claude Code
```

`cora install` also installs the `/cora-review` skill for Claude Code.

## Pitfalls

- `cora review` and `cora scan` silently fall back to deterministic checks when no API key is configured. Run `cora auth status` first if you expect an AI review.
- The graph commands (`brain`, `trace`, `callers`, `impact`, ...) depend on the index. Run `cora index` first and after large changes (or use `cora watch`).
- `--ci` exits 2 on any finding; `--severity` filters what is reported, so combine deliberately.
- Diffs over `--max-diff-size` (50000 chars default) are auto-chunked; very large reviews are slower and costlier. Review smaller scopes when possible.
- Do not use `cora commit --yolo`/`--force` to bypass a failing quality gate.
- Environment-specific: in agent sessions, run `cora` directly rather than chained with `cd x && cora ...` if your sandbox allow-lists by command prefix.
