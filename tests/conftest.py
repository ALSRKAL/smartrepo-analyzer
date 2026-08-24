"""Shared pytest fixtures: a realistic sample project on disk."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# make repository root importable when running from anywhere
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

MAIN_PY = '''"""Sample application entry point."""
import os
import json
from utils.helpers import format_name


def run(name, greeting=None):
    if not name:
        return "anonymous"
    if len(name) > 20:
        raise ValueError("name too long")
    return f"{greeting or 'Hello'} {format_name(name)}"


class App:
    def __init__(self, config_path="config.json"):
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path) as fh:
                self.config = json.load(fh)

    def start(self):
        return run(self.config.get("user", "world"))
'''


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a small but complete Python project."""
    root = tmp_path / "sample-project"
    (root / "utils").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / ".git").mkdir()          # should be ignored, never scanned
    (root / "node_modules" / "lib").mkdir(parents=True)

    (root / "main.py").write_text(MAIN_PY, encoding="utf-8")
    (root / "utils" / "__init__.py").write_text("", encoding="utf-8")
    (root / "utils" / "helpers.py").write_text(
        'def format_name(name):\n'
        '    parts = name.split()\n'
        '    if len(parts) > 1:\n'
        '        return " ".join(p.capitalize() for p in parts)\n'
        '    return name.capitalize()\n',
        encoding="utf-8",
    )
    (root / "app.js").write_text(
        "const express = require('express');\n"
        "function boot(port){\n  if(!port){ port=3000; }\n"
        "  const app = express();\n  app.listen(port);\n}\n"
        "class Server {}\nmodule.exports = {boot};\n",
        encoding="utf-8",
    )
    (root / "test_main.py").write_text(
        'def test_run():\n'
        '    from main import run\n'
        '    assert run("alice") == "Hello Alice"\n',
        encoding="utf-8",
    )
    # junk that must be ignored by the scanner
    (root / "node_modules" / "lib" / "junk.js").write_text("var x=1;\n", encoding="utf-8")
    (root / "requirements.txt").write_text("flask>=2.0\nrequests\n", encoding="utf-8")
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    return root


@pytest.fixture
def analyzed(sample_project: Path):
    """A fully analyzed ProjectStructure for the sample project."""
    from smartrepo_analyzer import CodeAnalyzer

    analyzer = CodeAnalyzer(str(sample_project))
    return analyzer.analyze_project(run_linters=False), sample_project
