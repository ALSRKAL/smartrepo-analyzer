"""Monorepo support: locate nested projects while ignoring vendor dirs.

دعم المستودعات متعددة المشاريع (monorepo) عبر اكتشاف ملفات الإعداد
المعروفة مع تجاهل مجلدات التبعيات المؤقتة.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Set

# Directories that never contain a *root* project worth analyzing on their own.
IGNORED_DIRS: Set[str] = {
    "node_modules", "__pycache__", ".git", ".hg", ".svn",
    "venv", ".venv", "env", ".env", "virtualenv",
    "dist", "build", "target", "out", ".next", ".nuxt",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".idea", ".vscode", "site-packages", ".eggs",
    "coverage", "htmlcov", "vendor", "bower_components",
}

PROJECT_MARKERS = (
    "package.json", "requirements.txt", "pyproject.toml", "Pipfile",
    "pubspec.yaml", "Cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "composer.json", "Gemfile",
)


def find_subprojects(root: Path) -> List[Path]:
    """Return directories that look like independent subprojects.

    يبحث عن مشاريع فرعية داخل المستودع. لا يعيد المجلد الجذر نفسه،
    ويتجاهل مجلدات التبعيات مثل node_modules تلقائيًا.
    """
    root = root.resolve()
    found: List[Path] = []
    seen: Set[Path] = set()

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name not in PROJECT_MARKERS:
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS for part in rel_parts[:-1]):
            continue
        parent = path.parent.resolve()
        if parent == root or parent in seen:
            continue
        # skip directories nested inside an already-found project
        if any(str(parent).startswith(str(existing) + "/") for existing in found):
            continue
        seen.add(parent)
        found.append(parent)

    return found
