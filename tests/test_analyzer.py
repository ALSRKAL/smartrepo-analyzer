"""Tests for the CodeAnalyzer core engine."""

from __future__ import annotations

import json
from pathlib import Path

from smartrepo_analyzer import CodeAnalyzer, FileInfo, compute_health_score


class TestProjectDetection:
    def test_detects_python_project(self, sample_project):
        info = CodeAnalyzer(str(sample_project)).detect_project_type()
        assert info["type"] == "Python"
        assert "Python" in info["languages"]
        assert "main.py" in info["entry_points"]
        assert info["framework"] == "Flask"

    def test_detects_node_project(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({
            "name": "web", "dependencies": {"react": "^18", "next": "^13"},
            "scripts": {"start": "next dev"},
        }))
        info = CodeAnalyzer(str(tmp_path)).detect_project_type()
        assert info["type"] == "Node.js"
        assert info["framework"] == "React"

    def test_falls_back_to_extensions(self, tmp_path):
        (tmp_path / "game.dart").write_text("void main(){}\n")
        info = CodeAnalyzer(str(tmp_path)).detect_project_type()
        assert info["type"] == "Dart"


class TestFileScanning:
    def test_ignores_junk_dirs(self, analyzed):
        structure, _ = analyzed
        paths = [f.path for f in structure.files]
        assert not any("node_modules" in p for p in paths)
        assert not any(".git" in p for p in paths)

    def test_supported_languages(self, analyzed):
        structure, _ = analyzed
        langs = {f.language for f in structure.files}
        assert "Python" in langs and "JavaScript" in langs

    def test_exclude_patterns(self, sample_project):
        analyzer = CodeAnalyzer(str(sample_project), exclude_patterns=["*.js"])
        files = analyzer._iter_project_files()
        assert all(f.suffix != ".js" for f in files)

    def test_include_patterns(self, sample_project):
        analyzer = CodeAnalyzer(str(sample_project), include_patterns=["*.py"])
        files = analyzer._iter_project_files()
        assert files and all(f.suffix == ".py" for f in files)


class TestPythonAnalysis:
    def test_extracts_functions_and_classes(self, analyzed):
        structure, _ = analyzed
        main = next(f for f in structure.files if f.path == "main.py")
        assert "run" in main.functions
        assert "App" in main.classes

    def test_complexity_counts_decisions(self, sample_project):
        analyzer = CodeAnalyzer(str(sample_project))
        info = analyzer.analyze_file(sample_project / "utils" / "helpers.py")
        # 1 base + 1 if + 1 comprehension-if inside genexpr => >=2
        assert info.complexity_score >= 2

    def test_imports_captured(self, analyzed):
        structure, _ = analyzed
        main = next(f for f in structure.files if f.path == "main.py")
        assert {"os", "json"} <= set(main.imports)
        assert "utils" in main.imports

    def test_docstring_extracted(self, analyzed):
        structure, _ = analyzed
        main = next(f for f in structure.files if f.path == "main.py")
        assert "Sample application" in main.docstring

    def test_binary_file_returns_none(self, tmp_path):
        (tmp_path / "blob.py").write_bytes(b"\x00\x01\x02\xff\xfe" * 100)
        analyzer = CodeAnalyzer(str(tmp_path))
        assert analyzer.analyze_file(tmp_path / "blob.py") is None


class TestJSTSAnalysis:
    def test_js_functions_and_classes(self, analyzed):
        structure, _ = analyzed
        js = next(f for f in structure.files if f.path == "app.js")
        assert "boot" in js.functions
        assert "Server" in js.classes
        assert "express" in js.imports


class TestDependencyGraph:
    def test_local_import_edges(self, analyzed):
        structure, _ = analyzed
        graph = structure.file_dependency_graph
        assert graph is not None
        # main.py imports utils.helpers -> edge to utils/helpers.py
        edges = set(graph.get("main.py", []))
        assert "utils/helpers.py" in edges

    def test_graph_is_sparse_not_quadratic_output(self, analyzed):
        structure, _ = analyzed
        graph = structure.file_dependency_graph
        total_edges = sum(len(v) for v in graph.values())
        assert total_edges < len(structure.files) ** 2


class TestMetrics:
    def test_metrics_shape(self, analyzed):
        structure, _ = analyzed
        m = structure.metrics
        assert m["total_files"] >= 3
        assert m["total_lines"] > m["code_lines"] > 0
        assert m["average_complexity"] >= 1
        assert "Python" in m["language_distribution"]

    def test_architecture_categories(self, analyzed):
        structure, _ = analyzed
        assert structure.architecture["Tests"], "test file must be categorized"
        assert structure.architecture["Utils"]

    def test_framework_detection(self, analyzed):
        structure, _ = analyzed
        assert isinstance(structure.detected_frameworks, list)
        assert "express" in structure.detected_frameworks


class TestParallelConsistency:
    def test_parallel_equals_sequential(self, sample_project):
        a1 = CodeAnalyzer(str(sample_project), max_workers=4)
        a2 = CodeAnalyzer(str(sample_project), max_workers=1)
        s1 = a1.analyze_project(run_linters=False)
        s2 = a2.analyze_project(run_linters=False)
        assert {(f.path, f.complexity_score) for f in s1.files} == \
               {(f.path, f.complexity_score) for f in s2.files}


class TestHealthScore:
    def test_perfect_project_scores_high(self, analyzed):
        structure, _ = analyzed
        assert structure.health["score"] >= 70
        assert structure.health["grade"] in ("A+", "A", "B")

    def test_no_tests_penalized(self):
        score = compute_health_score(
            metrics={"total_files": 10, "average_complexity": 15},
            test_ratio=0.0,
        )["score"]
        healthy = compute_health_score(
            metrics={"total_files": 10, "average_complexity": 1},
            test_ratio=0.4,
            overall_coverage=95,
        )["score"]
        assert score < healthy
        assert healthy >= 90

    def test_security_issues_reduce_score(self):
        clean = compute_health_score(
            metrics={"total_files": 10, "average_complexity": 2}, test_ratio=0.2)["score"]
        vulnerable = compute_health_score(
            metrics={"total_files": 10, "average_complexity": 2}, test_ratio=0.2,
            security_counts={"HIGH": 5})["score"]
        assert vulnerable < clean - 10

    def test_score_bounded(self):
        worst = compute_health_score(
            metrics={"total_files": 5, "average_complexity": 50}, test_ratio=0.0,
            lint_issue_count=500, security_counts={"HIGH": 50},
            overall_coverage=0)
        assert 0 <= worst["score"] <= 100

    def test_breakdown_explains_factors(self):
        result = compute_health_score(
            metrics={"total_files": 10, "average_complexity": 2}, test_ratio=0.3)
        assert set(result["breakdown"]) >= {"complexity", "tests", "linting", "security"}
