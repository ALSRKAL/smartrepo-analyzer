"""End-to-end CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "smartrepo_analyzer.py"


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=180, cwd=cwd or str(REPO_ROOT),
    )


class TestAnalyzeCommand:
    def test_analyze_generates_outputs(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        (project / "main.py").write_text("print('hi')\n", encoding="utf-8")
        out = tmp_path / "results"

        proc = run_cli("analyze", str(project), "-o", str(out), "--no-lint", "-q")
        assert proc.returncode == 0, proc.stderr
        for name in ("readme-enhanced.md", "ai-summary.json", "report.html"):
            assert (out / name).exists(), f"{name} not generated"

    def test_missing_path_fails_gracefully(self, tmp_path):
        proc = run_cli("analyze", str(tmp_path / "does-not-exist"), "--no-lint", "-q")
        assert proc.returncode != 0

    def test_version_flag(self):
        proc = run_cli("--version")
        assert "12.0.1" in proc.stdout + proc.stderr


class TestHelpCommand:
    def test_help_prints_commands(self):
        proc = run_cli("help")
        assert "analyze" in proc.stdout
        assert "gui" in proc.stdout


class TestCreateRequirements:
    def test_creates_file_in_cwd(self, tmp_path, monkeypatch):
        import smartrepo_analyzer as sra

        monkeypatch.chdir(tmp_path)
        assert sra.main(["create-requirements"]) == 0
        content = (tmp_path / "requirements.txt").read_text(encoding="utf-8")
        assert "rich" in content


class TestExitCodes:
    def test_success_zero(self, tmp_path):
        project = tmp_path / "p"
        project.mkdir()
        (project / "a.py").write_text("x = 1\n", encoding="utf-8")
        assert run_cli("analyze", str(project), "--no-lint", "-q",
                       "-o", str(tmp_path / "o")).returncode == 0
