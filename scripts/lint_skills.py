#!/usr/bin/env python3
"""Lint skills/*/SKILL.md frontmatter (stdlib only).

Rules: frontmatter between leading '---' lines; `name` is lowercase
letters/digits/hyphens and equals the parent directory name; `description`
is non-empty. Exit 1 listing violations, else 0.

Usage: lint_skills.py [--selftest]
"""
import re
import sys
import tempfile
from pathlib import Path

NAME_RE = re.compile(r"[a-z0-9-]+")


def parse_frontmatter(text):
    """Return {key: value} for top-level 'key: value' lines, or None if absent."""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        # ponytail: top-level scalars only; folded/block values count as empty
        m = re.match(r"([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("\"'")
    return None  # unterminated


def lint(root):
    errors = []
    for path in sorted(Path(root).glob("skills/*/SKILL.md")):
        rel = path.relative_to(root)
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(f"{rel}: missing or unterminated YAML frontmatter")
            continue
        name = fm.get("name", "")
        if not name:
            errors.append(f"{rel}: missing 'name'")
        elif not NAME_RE.fullmatch(name):
            errors.append(f"{rel}: name '{name}' must be lowercase letters, digits, hyphens")
        elif name != path.parent.name:
            errors.append(f"{rel}: name '{name}' must equal directory '{path.parent.name}'")
        if not fm.get("description"):
            errors.append(f"{rel}: missing or empty 'description'")
    return errors


def selftest():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert lint(root) == [], "no skills must pass"
        good = root / "skills" / "good-skill"
        good.mkdir(parents=True)
        (good / "SKILL.md").write_text("---\nname: good-skill\ndescription: Does a thing.\n---\n# Good\n")
        assert lint(root) == [], "good fixture must pass"
        bad = root / "skills" / "bad-skill"
        bad.mkdir()
        (bad / "SKILL.md").write_text("---\nname: Other_Name\ndescription:\n---\n")
        errs = lint(root)
        assert len(errs) == 2 and all("bad-skill" in e for e in errs), errs
        (bad / "SKILL.md").write_text("---\nname: wrong-dir\ndescription: x\n---\n")
        assert "must equal directory" in lint(root)[0]
        (bad / "SKILL.md").write_text("no frontmatter\n")
        assert "frontmatter" in lint(root)[0]
    print("selftest OK")


def main():
    if "--selftest" in sys.argv[1:]:
        selftest()
        return 0
    errors = lint(Path.cwd())
    if errors:
        print("Skill lint failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("Skill lint OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
