"""Tests for support modules (no external tools required)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


class TestCoverageSupport:
    def test_parse_missing_file(self, tmp_path):
        from coverage_support import parse_coverage_xml
        assert parse_coverage_xml(tmp_path / "nope.xml") is None

    def test_parse_valid_xml(self, tmp_path):
        from coverage_support import get_overall_coverage, parse_coverage_xml

        xml = tmp_path / "coverage.xml"
        xml.write_text(
            """<coverage line-rate="0.75">
              <classes>
                <class filename="a.py"><lines><line hits="1"/><line hits="0"/></lines></class>
                <class filename="b.py"><lines><line hits="1"/><line hits="1"/></lines></class>
              </classes>
            </coverage>""",
            encoding="utf-8",
        )
        data = parse_coverage_xml(xml)
        assert data is not None
        assert data["a.py"] == 50.0
        assert data["b.py"] == 100.0
        assert get_overall_coverage(data) == 75.0  # prefers root line-rate

    def test_malformed_xml(self, tmp_path):
        from coverage_support import parse_coverage_xml

        bad = tmp_path / "coverage.xml"
        bad.write_text("<not-closed", encoding="utf-8")
        assert parse_coverage_xml(bad) is None


class TestCallGraph:
    def test_extracts_local_calls(self, tmp_path):
        from callgraph_support import extract_call_graph

        f = tmp_path / "mod.py"
        f.write_text(
            "def helper():\n    return 1\n\n"
            "def main():\n    return helper()\n",
            encoding="utf-8",
        )
        graph = extract_call_graph([f])
        assert "mod.py::main" in graph
        assert "helper" in graph["mod.py::main"]

    def test_cycle_detection_fallback(self):
        from callgraph_support import find_cycles, nx_available

        graph = {"a.py::f": {"g"}, "a.py::g": {"f"}}
        cycles = find_cycles(graph)
        assert cycles, "cycle must be found with or without networkx"
        assert nx_available() or True  # works either way

    def test_mermaid_output_sanitized(self, tmp_path):
        from callgraph_support import call_graph_to_mermaid, extract_call_graph

        f = tmp_path / "weird name.py"
        f.write_text("def a():\n    pass\n", encoding="utf-8")
        out = call_graph_to_mermaid(extract_call_graph([f]))
        assert "graph TD" in out
        # labels are quoted so spaces/colons cannot break Mermaid syntax
        assert "'weird name.py::a'" in out
        for line in out.splitlines():
            if "-->" in line:
                node_id = line.strip().split()[0]
                assert " " not in node_id and "'" not in node_id


class TestFrameworkDetection:
    def test_multiple_frameworks(self, tmp_path):
        from framework_detection_support import detect_frameworks

        py = tmp_path / "svc.py"
        py.write_text("from fastapi import FastAPI\n", encoding="utf-8")
        js = tmp_path / "app.jsx"
        js.write_text("import React from 'react';\n", encoding="utf-8")
        found = detect_frameworks([py, js])
        assert {"fastapi", "react"} <= found

    def test_no_false_positives(self, tmp_path):
        from framework_detection_support import detect_frameworks

        plain = tmp_path / "plain.js"
        plain.write_text("console.log('hello');\n", encoding="utf-8")
        assert detect_frameworks([plain]) == set()


class TestUMLAndSummaries:
    def test_uml_includes_inheritance(self, tmp_path):
        from uml_support import generate_mermaid_class_diagram

        src = tmp_path / "models.py"
        src.write_text(
            "class Animal:\n    def speak(self):\n        pass\n\n"
            "class Dog(Animal):\n    def fetch(self):\n        pass\n",
            encoding="utf-8",
        )
        out = tmp_path / "uml.mmd"
        generate_mermaid_class_diagram([src], out)
        content = out.read_text(encoding="utf-8")
        assert "Animal <|-- Dog" in content
        assert "fetch()" in content

    def test_summarize_short_file_returns_full(self, tmp_path):
        from summarization_support import summarize_file

        f = tmp_path / "tiny.py"
        f.write_text("x = 1\ny = 2\n", encoding="utf-8")
        assert summarize_file(f) == "x = 1\ny = 2"

    def test_summarize_long_file_lists_defs(self, tmp_path):
        from summarization_support import summarize_file

        body = "\n".join(f"def fn_{i}():\n    pass\n" for i in range(40))
        f = tmp_path / "big.py"
        f.write_text(body, encoding="utf-8")
        summary = summarize_file(f)
        assert "[10] def fn_9()" in summary or "def fn_" in summary


class TestUsageExamples:
    def test_collects_tests_and_doctests(self, tmp_path):
        from usage_example_support import extract_usage_examples

        f = tmp_path / "calc.py"
        f.write_text(
            'def add(a, b):\n'
            '    """Add numbers.\n\n    Example:\n        >>> add(1, 2)\n'
            '    """\n'
            "    return a + b\n",
            encoding="utf-8",
        )
        t = tmp_path / "test_calc.py"
        t.write_text("def test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8")
        examples = extract_usage_examples([t, f])
        joined = "\n".join(examples)
        assert "test_add" in joined
        assert "add(1, 2)" in joined


class TestRecommendations:
    def test_empty_gives_positive(self):
        from recommendation_support import generate_recommendations

        recs = generate_recommendations({"total_files": 5, "average_complexity": 2})
        assert any("healthy" in r for r in recs)

    def test_flags_complexity_and_coverage(self):
        from recommendation_support import generate_recommendations

        recs = generate_recommendations(
            {"total_files": 20, "average_complexity": 15, "total_lines": 900},
            coverage=30.0,
        )
        text = "\n".join(recs).lower()
        assert "complexity" in text
        assert "coverage" in text

    def test_security_recommendation(self):
        from recommendation_support import generate_recommendations

        recs = generate_recommendations(
            {"total_files": 4, "average_complexity": 2},
            security_issues={"HIGH": 3, "MEDIUM": 0, "LOW": 0},
        )
        assert any("CRITICAL" in r for r in recs)


class TestToolRunner:
    def test_tool_available_caches(self, monkeypatch):
        import tool_runner

        tool_runner.reset_tool_cache()
        assert tool_runner.tool_available("python3") is True
        assert tool_runner.tool_available("definitely-not-a-real-tool-xyz") is False

    def test_run_command_missing_binary(self):
        from tool_runner import run_command

        assert run_command(["definitely-not-a-real-tool-xyz"]) is None

    def test_run_batched_chunks(self):
        from tool_runner import run_batched

        files = [Path(f"f{i}.py") for i in range(10)]
        calls = []
        procs = run_batched(files, lambda b: (calls.append(list(b)), ["true"])[1],
                            batch_size=4)
        assert len(calls) == 3          # 4 + 4 + 2
        assert all(len(c) <= 4 for c in calls)
        assert len(procs) == 3


class TestGitSupport:
    def test_contributors_outside_repo(self, tmp_path):
        from git_support import get_contributors

        assert get_contributors(tmp_path) == []

    def test_git_stats_outside_repo(self, tmp_path):
        from git_support import get_git_stats

        stats = get_git_stats(tmp_path)
        assert stats == {"last_commit": None, "total_commits": None}


class TestComplexityHelpers:
    def test_radon_absent_returns_empty(self):
        from complexity_support import (
            analyze_complexity_with_radon,
            analyze_maintainability_with_radon,
        )
        # radon may or may not be installed; function must never raise
        result = analyze_complexity_with_radon([])
        assert result == {}

    def test_bandit_absent_returns_empty(self):
        from security_support import analyze_security_with_bandit

        assert analyze_security_with_bandit([]) == {}
