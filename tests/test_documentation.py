"""Tests for DocumentationGenerator artifacts."""

from __future__ import annotations

import json
from pathlib import Path


EXPECTED_FILES = [
    "readme-enhanced.md",
    "architecture.mmd",
    "ai-summary.json",
    "prompt-ready.md",
    "recommendations.txt",
    "report.html",
    "uml-class-diagram.mmd",
]


class TestGeneratedArtifacts:
    def test_all_core_files_generated(self, tmp_path, analyzed):
        structure, project_root = analyzed
        from smartrepo_analyzer import DocumentationGenerator

        out = tmp_path / "out"
        gen = DocumentationGenerator(structure, out, project_root=project_root)
        generated = gen.generate_all()
        for name in EXPECTED_FILES:
            assert (out / name).exists(), f"missing artifact: {name}"
            assert name in generated

    def test_ai_summary_content(self, tmp_path, analyzed):
        structure, root = analyzed
        from smartrepo_analyzer import DocumentationGenerator

        out = tmp_path / "out"
        DocumentationGenerator(structure, out, project_root=root).generate_all()
        data = json.loads((out / "ai-summary.json").read_text(encoding="utf-8"))
        assert data["project_overview"]["name"] == structure.name
        assert data["metrics"]["total_files"] == structure.metrics["total_files"]
        assert data["health"]["grade"]
        assert data["generated_at"].endswith("Z")
        # dynamic timestamp, not the old hardcoded date
        assert not data["generated_at"].startswith("2025-07-23")

    def test_readme_contains_health(self, tmp_path, analyzed):
        structure, root = analyzed
        from smartrepo_analyzer import DocumentationGenerator

        out = tmp_path / "out"
        DocumentationGenerator(structure, out, project_root=root).generate_all()
        readme = (out / "readme-enhanced.md").read_text(encoding="utf-8")
        assert "Health Score" in readme
        assert structure.name in readme

    def test_html_report_is_standalone(self, tmp_path, analyzed):
        structure, root = analyzed
        from smartrepo_analyzer import DocumentationGenerator

        out = tmp_path / "out"
        DocumentationGenerator(structure, out, project_root=root).generate_all()
        html = (out / "report.html").read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert structure.name in html
        assert "Health Score" in html

    def test_dependency_graph_written_when_edges_exist(self, tmp_path, analyzed):
        structure, root = analyzed
        from smartrepo_analyzer import DocumentationGenerator

        out = tmp_path / "out"
        DocumentationGenerator(structure, out, project_root=root).generate_all()
        graph = (out / "file-dependency-graph.mmd").read_text(encoding="utf-8")
        assert "graph TD" in graph
        assert "-->" in graph

    def test_prompt_ready_mentions_languages(self, tmp_path, analyzed):
        structure, root = analyzed
        from smartrepo_analyzer import DocumentationGenerator

        out = tmp_path / "out"
        DocumentationGenerator(structure, out, project_root=root).generate_all()
        prompt = (out / "prompt-ready.md").read_text(encoding="utf-8")
        assert "Python" in prompt
        assert "AI-Ready Project Analysis" in prompt

    def test_custom_output_dir_outside_project(self, tmp_path, sample_project):
        """Regression: generators must read sources via project_root,
        even when output lives far away from the analyzed project."""
        from smartrepo_analyzer import CodeAnalyzer, DocumentationGenerator

        analyzer = CodeAnalyzer(str(sample_project))
        structure = analyzer.analyze_project(run_linters=False)
        far_out = tmp_path / "deeply" / "nested" / "analysis-out"
        gen = DocumentationGenerator(structure, far_out, project_root=sample_project)
        gen.generate_all()
        assert (far_out / "uml-class-diagram.mmd").exists()


class TestMonorepoMode:
    def test_subprojects_detected_and_root_excluded(self, tmp_path):
        (tmp_path / "packages" / "alpha").mkdir(parents=True)
        (tmp_path / "packages" / "beta").mkdir(parents=True)
        (tmp_path / "node_modules" / "evil").mkdir(parents=True)
        (tmp_path / "packages" / "alpha" / "package.json").write_text("{}")
        (tmp_path / "packages" / "beta" / "requirements.txt").write_text("flask\n")
        (tmp_path / "package.json").write_text("{}")  # root itself -> ignored
        (tmp_path / "node_modules" / "evil" / "package.json").write_text("{}")

        from monorepo_support import find_subprojects

        subs = find_subprojects(tmp_path)
        names = {s.name for s in subs}
        assert names == {"alpha", "beta"}
