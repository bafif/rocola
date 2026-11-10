"""The repository's documents: each one in Spanish and in English, and no broken links.

A document X.md has its other language next to it as X.en.md or X.es.md (README.md is the
English one, with README.es.md). Not documents of their own: CLAUDE.md, licenses, changelogs
and the GitHub templates under .github/.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\]\(([^)\s]+)\)")


def documents() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "*.md"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("needs a git checkout of the repository")
    return [p for p in out.splitlines() if p and not _skipped(p)]


def _skipped(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        path.startswith(".github/")
        or name == "CLAUDE.md"
        or name.upper().startswith(("LICENSE", "CHANGELOG"))
    )


def _others(path: str) -> list[str]:
    for suffix in (".en.md", ".es.md"):
        if path.endswith(suffix):
            return [path[: -len(suffix)] + ".md"]
    stem = path[: -len(".md")]
    return [stem + ".en.md", stem + ".es.md"]


def test_every_document_is_in_both_languages():
    docs = set(documents())
    missing = [
        f"{path}: missing {' or '.join(_others(path))}"
        for path in sorted(docs)
        if not any(other in docs for other in _others(path))
    ]
    assert not missing, "documents without their other language:\n" + "\n".join(missing)


def test_relative_links_lead_to_a_file():
    broken = []
    for path in documents():
        base = (REPO / path).parent
        for n, line in enumerate((REPO / path).read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK.findall(line):
                if target.startswith("#") or re.match(r"^[a-z][a-z0-9+.-]*:", target):
                    continue
                if not (base / target.split("#", 1)[0]).exists():
                    broken.append(f"{path}:{n} {target}")
    assert not broken, "broken links:\n" + "\n".join(broken)
