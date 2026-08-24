#!/usr/bin/env python3
"""
SmartRepo Analyzer — AI-Powered Code Analysis & Documentation Tool

A comprehensive, fast, bilingual tool that scans a codebase, extracts deep
metrics (structure, dependencies, complexity, security, coverage) and
generates AI-ready documentation: enhanced README, Mermaid diagrams,
JSON summaries, prompt-ready context and an interactive HTML report.

SmartRepo Analyzer — أداة تحليل أكواد ذكية ثنائية اللغة تفحص المشروع،
تستخرج مقاييس معمّقة (بنية، تبعيات، تعقيد، أمان، تغطية) وتولّد توثيقًا
جاهزًا للذكاء الاصطناعي: README محسّن، مخططات Mermaid، ملخصات JSON،
سياق جاهز للنماذج اللغوية، وتقرير HTML تفاعلي.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

# Core dependencies
try:
    import yaml  # noqa: F401  (used by downstream generators)
    import toml  # noqa: F401
    from pygments.lexers import get_lexer_for_filename
    from pygments.util import ClassNotFound
except ImportError:
    print("Missing dependencies. Install with: pip install rich pygments pyyaml toml")
    sys.exit(1)

# --- internal support modules -------------------------------------------
from ai_summarization_support import ai_summarize_code
from callgraph_support import extract_call_graph, find_cycles, save_call_graph_mermaid
from complexity_support import (
    analyze_complexity_with_radon,
    analyze_maintainability_with_radon,
)
from coverage_support import get_overall_coverage, parse_coverage_xml
from deep_analysis import ClassInfo, FunctionInfo, parse_source
from framework_detection_support import detect_frameworks
from git_support import get_contributors, get_git_stats
from linting_support import run_pylint_on_files
from monorepo_support import find_subprojects
from multi_lint_support import run_eslint_on_files, run_flake8_on_files
from recommendation_support import generate_recommendations
from security_support import analyze_security_with_bandit
from summarization_support import summarize_file
from tool_runner import tool_available
from uml_support import generate_mermaid_class_diagram
from usage_example_support import extract_usage_examples

__version__ = "12.0.1"
ANALYZER_VERSION = __version__

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React JSX",
    ".tsx": "React TSX",
    ".dart": "Dart",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".php": "PHP",
    ".rb": "Ruby",
    ".scala": "Scala",
    ".c": "C",
    ".h": "C Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
}

IGNORED_DIRS: Set[str] = {
    "node_modules", "__pycache__", ".git", ".hg", ".svn", "venv", ".venv",
    "env", ".env", "virtualenv", "dist", "build", "target", "out",
    ".next", ".nuxt", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".idea", ".vscode", "site-packages", ".eggs", "*.egg-info",
    "coverage", "htmlcov", "vendor", "bower_components",
    "smartrepo-analysis", ".jython_cache", "__macosx",
}

MAX_FILE_SIZE_BYTES = 1_500_000  # skip giant generated/binary-ish sources


def utc_now_iso() -> str:
    """Current UTC timestamp in ISO-8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _match_any(name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(name.lower(), pat.lower()) for pat in patterns)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class FileInfo:
    """Information about a single analyzed source file."""

    path: str
    language: str
    size: int
    lines: int
    functions: List[str]
    classes: List[str]
    imports: List[str]
    complexity_score: int
    summary: str
    code_lines: int = 0
    docstring: str = ""
    functions_detail: List[FunctionInfo] = field(default_factory=list)
    classes_detail: List[ClassInfo] = field(default_factory=list)
    todos: int = 0
    endpoints: List[str] = field(default_factory=list)

    @property
    def documented_pct(self) -> float:
        syms = [f for f in self.functions_detail if not f.name.startswith("_")]
        if not syms:
            return 100.0 if self.docstring else 0.0
        return 100.0 * sum(1 for f in syms if f.documented) / len(syms)


@dataclass
class ProjectStructure:
    """Complete result of analyzing one project."""

    name: str
    type: str
    languages: List[str]
    entry_points: List[str]
    dependencies: Dict[str, List[str]]
    files: List[FileInfo]
    architecture: Dict[str, List[str]]
    metrics: Dict[str, Any]
    framework: Optional[str] = None
    package_managers: List[str] = field(default_factory=list)
    file_dependency_graph: Optional[Dict[str, List[str]]] = None
    coverage: Optional[dict] = None
    overall_coverage: Optional[float] = None
    linting: Optional[list] = None
    call_graph_cycles: Optional[List[List[str]]] = None
    detected_frameworks: Optional[List[str]] = None
    contributors: Optional[List[Dict[str, Any]]] = None
    git_stats: Optional[Dict[str, Any]] = None
    flake8: Optional[List[Dict[str, Any]]] = None
    eslint: Optional[List[Dict[str, Any]]] = None
    complexity: Optional[Dict[str, Any]] = None
    maintainability: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None
    ai_summaries: Optional[Dict[str, str]] = None
    health: Optional[Dict[str, Any]] = None
    generated_at: str = field(default_factory=utc_now_iso)


# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------


def compute_health_score(
    metrics: Dict[str, Any],
    test_ratio: float,
    lint_issue_count: int = 0,
    security_counts: Optional[Dict[str, int]] = None,
    overall_coverage: Optional[float] = None,
    avg_maintainability: Optional[float] = None,
    documented_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """Compute an overall project health score (0-100) plus letter grade.

    يحسب درجة صحة المشروع الإجمالية من 100 مع تقدير حرفي، بناءً على
    التعقيد، التغطية الاختبارية، مشاكل الفحص الثابت، الأمان، والتوثيق.
    """
    score = 100.0
    breakdown: Dict[str, str] = {}

    avg_complexity = float(metrics.get("average_complexity") or 0)

    if avg_complexity > 12:
        penalty = min(25, (avg_complexity - 12) * 2.5)
        score -= penalty
        breakdown["complexity"] = f"very high ({avg_complexity:.1f}) −{penalty:.0f}"
    elif avg_complexity > 6:
        penalty = (avg_complexity - 6) * 2.5
        score -= penalty
        breakdown["complexity"] = f"high ({avg_complexity:.1f}) −{penalty:.0f}"
    else:
        breakdown["complexity"] = f"ok ({avg_complexity:.1f})"

    if test_ratio >= 0.20:
        breakdown["tests"] = f"good ratio ({test_ratio:.0%})"
        score += 3
    elif test_ratio >= 0.10:
        breakdown["tests"] = f"fair ratio ({test_ratio:.0%})"
    elif test_ratio > 0:
        score -= 10
        breakdown["tests"] = f"low ratio ({test_ratio:.0%}) −10"
    else:
        score -= 18
        breakdown["tests"] = "no tests found −18"

    total_files = max(metrics.get("total_files", 1), 1)
    density = lint_issue_count / total_files
    if density > 10:
        score -= 15
        breakdown["linting"] = f"{density:.0f} issues/file −15"
    elif density > 4:
        score -= 7
        breakdown["linting"] = f"{density:.0f} issues/file −7"
    elif density > 0:
        score -= 3
        breakdown["linting"] = f"{density:.0f} issues/file −3"
    else:
        breakdown["linting"] = "clean"

    sec_counts = security_counts or {}
    high = sec_counts.get("HIGH", 0)
    med = sec_counts.get("MEDIUM", 0)
    if high:
        pen = min(25, high * 6)
        score -= pen
        breakdown["security"] = f"{high} high-severity issues −{pen}"
    elif med:
        pen = min(10, med * 2)
        score -= pen
        breakdown["security"] = f"{med} medium issues −{pen}"
    else:
        breakdown["security"] = "no known issues"

    if overall_coverage is not None:
        if overall_coverage >= 80:
            breakdown["coverage"] = f"{overall_coverage:.0f}% strong"
            score += 5
        elif overall_coverage >= 50:
            breakdown["coverage"] = f"{overall_coverage:.0f}% moderate"
        else:
            pen = min(12, (50 - overall_coverage) / 4)
            score -= pen
            breakdown["coverage"] = f"{overall_coverage:.0f}% low −{pen:.0f}"

    if avg_maintainability is not None and avg_maintainability < 40:
        score -= 8
        breakdown["maintainability"] = f"MI {avg_maintainability:.0f} low −8"

    if documented_pct is not None:
        if documented_pct >= 60:
            bonus = 4
            score += bonus
            breakdown["documentation"] = f"{documented_pct:.0f}% symbols documented +{bonus}"
        elif documented_pct < 20:
            pen = 5
            score -= pen
            breakdown["documentation"] = f"{documented_pct:.0f}% documented −{pen}"
        else:
            breakdown["documentation"] = f"{documented_pct:.0f}% documented"

    score = max(0.0, min(100.0, score))
    if score >= 90:
        grade = "A+"
    elif score >= 80:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 55:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": round(score),
        "grade": grade,
        "breakdown": breakdown,
    }


# ---------------------------------------------------------------------------
# Core analyzer
# ---------------------------------------------------------------------------


class CodeAnalyzer:
    """Core code-analysis engine (parallel, configurable, resilient)."""

    def __init__(
        self,
        project_path: str,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        verbose: bool = False,
        max_workers: Optional[int] = None,
    ):
        self.project_path = Path(project_path).resolve()
        self.project_structure: Optional[ProjectStructure] = None
        self.exclude_patterns = list(exclude_patterns or [])
        self.include_patterns = list(include_patterns or [])
        self.verbose = verbose
        self.max_workers = max_workers or min(8, (os.cpu_count() or 2))

    # ------------------------------------------------------------- logging
    def _log(self, msg: str) -> None:
        if self.verbose:
            console.log(msg)

    # ------------------------------------------------------------ scanning
    def _iter_project_files(self) -> List[Path]:
        """Collect candidate files while honoring ignores/excludes/includes.

        يجمع الملفات المرشحة للتحليل متجاهلًا المجلدات المؤقتة والتبعيات،
        مع دعم أنماط استبعاد/تضمين مخصصة من المستخدم.
        """
        results: List[Path] = []
        root_str = str(self.project_path)
        for dirpath, dirnames, filenames in os.walk(root_str):
            rel_dir = os.path.relpath(dirpath, root_str)
            # prune ignored directories early
            dirnames[:] = [
                d for d in dirnames
                if d not in IGNORED_DIRS
                and not _match_any(d, ["*.egg-info"])
                and not _match_any(d, self.exclude_patterns)
                and not d.startswith(".")
            ]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                rel_path = os.path.normpath(os.path.join(rel_dir, fname)) if rel_dir != "." else fname
                if _match_any(rel_path, self.exclude_patterns):
                    continue
                if self.include_patterns and not (
                    _match_any(rel_path, self.include_patterns)
                    or _match_any(fname, self.include_patterns)
                ):
                    continue
                full = Path(dirpath) / fname
                try:
                    if full.stat().st_size > MAX_FILE_SIZE_BYTES:
                        self._log(f"Skipping oversized file: {rel_path}")
                        continue
                except OSError:
                    continue
                results.append(full)
        return sorted(results)

    def detect_project_type(self) -> Dict[str, Any]:
        """Auto-detect project type, framework and entry points."""
        info: Dict[str, Any] = {
            "type": "Unknown",
            "framework": None,
            "languages": [],
            "package_managers": [],
            "entry_points": [],
        }

        detectors: Dict[str, Any] = {
            "package.json": self._analyze_package_json,
            "pyproject.toml": self._analyze_pyproject,
            "requirements.txt": self._analyze_requirements,
            "Pipfile": self._analyze_pipfile,
            "pubspec.yaml": self._analyze_pubspec,
            "Cargo.toml": self._analyze_cargo,
            "go.mod": self._analyze_go_mod,
            "pom.xml": self._analyze_maven,
            "build.gradle": self._analyze_gradle,
            "composer.json": self._analyze_composer,
            "Gemfile": self._analyze_ruby,
        }
        # order matters: most specific first
        for config_file in [
            "pubspec.yaml", "Cargo.toml", "go.mod", "pyproject.toml",
            "requirements.txt", "Pipfile", "pom.xml", "build.gradle",
            "composer.json", "Gemfile", "package.json",
        ]:
            config_path = self.project_path / config_file
            if config_path.exists():
                result = detectors[config_file](config_path)
                info.update({k: v for k, v in result.items() if v is not None})
                break

        if info["type"] == "Unknown":
            info.update(self._analyze_by_extensions())

        return info

    # ----------------------------------------------------- config analyzers
    def _read_json(self, path: Path) -> Optional[dict]:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _analyze_pyproject(self, path: Path) -> Dict[str, Any]:
        data = self._read_json(path.parent / "poetry.lock")  # poetry hint only
        try:
            with open(path, encoding="utf-8") as f:
                content = toml.load(f)
        except Exception:
            content = {}
        project_meta = content.get("project", {}) if isinstance(content, dict) else {}
        poetry_meta = content.get("tool", {}).get("poetry", {}) if isinstance(content, dict) else {}

        deps = set()
        deps.update((project_meta.get("dependencies") or {}).keys())
        deps.update((poetry_meta.get("dependencies") or {}).keys())
        deps.discard("python")

        framework = None
        frameworks = {
            "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
            "tornado": "Tornado", "streamlit": "Streamlit", "click": "Click",
        }
        for pkg, fw in frameworks.items():
            if any(p.lower().startswith(pkg) for p in deps):
                framework = fw
                break

        scripts = list((project_meta.get("scripts") or {}).keys()) if isinstance(project_meta.get("scripts"), dict) else []

        return {
            "type": "Python",
            "framework": framework,
            "languages": ["Python"],
            "package_managers": ["pip", "poetry" if poetry_meta else "pip"],
            "entry_points": self._find_python_entry_points() + [s for s in scripts if s != "_"],
        }

    def _analyze_package_json(self, path: Path) -> Dict[str, Any]:
        data = self._read_json(path) or {}
        deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        dep_names = {k.split("/")[0] for k in deps}
        languages = ["JavaScript"]

        framework = None
        checks = [
            (("react",), "React"),
            (("vue",), "Vue.js"),
            (("@angular/core", "angular"), "Angular"),
            (("express",), "Express.js"),
            (("next",), "Next.js"),
            (("nuxt",), "Nuxt"),
            (("svelte",), "Svelte"),
            (("electron",), "Electron"),
        ]
        for keys, name in checks:
            if set(keys) & dep_names:
                framework = name
                break

        if "typescript" in dep_names or any(
            p.suffix == ".ts" for p in list(self.project_path.glob("*.ts"))[:5]
        ):
            languages.append("TypeScript")

        entry_points: List[str] = []
        if data.get("main"):
            entry_points.append(data["main"])
        start = (data.get("scripts") or {}).get("start", "")
        m = re.search(r"(?:node|ts-node|tsx|bun|deno\s+run)\s+([\w./-]+)", start)
        if m:
            entry_points.append(m.group(1))

        managers = ["npm"]
        if (self.project_path / "yarn.lock").exists():
            managers.append("yarn")
        if (self.project_path / "pnpm-lock.yaml").exists():
            managers.append("pnpm")

        return {
            "type": "Node.js",
            "framework": framework,
            "languages": languages,
            "package_managers": managers,
            "entry_points": entry_points,
        }

    def _analyze_requirements(self, path: Path) -> Dict[str, Any]:
        frameworks = {
            "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
            "tornado": "Tornado", "streamlit": "Streamlit",
            "scipy": "Scientific/ML", "tensorflow": "TensorFlow",
            "torch": "PyTorch", "scikit-learn": "Scikit-learn",
        }
        try:
            content = path.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            content = ""
        detected = next((fw for pkg, fw in frameworks.items() if pkg in content), None)
        return {
            "type": "Python",
            "framework": detected,
            "languages": ["Python"],
            "package_managers": ["pip"],
            "entry_points": self._find_python_entry_points(),
        }

    def _analyze_pipfile(self, path: Path) -> Dict[str, Any]:
        return {
            "type": "Python",
            "languages": ["Python"],
            "package_managers": ["pipenv"],
            "entry_points": self._find_python_entry_points(),
        }

    def _analyze_pubspec(self, path: Path) -> Dict[str, Any]:
        return {
            "type": "Flutter",
            "framework": "Flutter",
            "languages": ["Dart"],
            "package_managers": ["pub"],
            "entry_points": ["lib/main.dart"],
        }

    def _analyze_cargo(self, path: Path) -> Dict[str, Any]:
        return {
            "type": "Rust",
            "languages": ["Rust"],
            "package_managers": ["cargo"],
            "entry_points": ["src/main.rs"],
        }

    def _analyze_go_mod(self, path: Path) -> Dict[str, Any]:
        return {
            "type": "Go",
            "languages": ["Go"],
            "package_managers": ["go mod"],
            "entry_points": ["main.go"],
        }

    def _analyze_maven(self, path: Path) -> Dict[str, Any]:
        return {
            "type": "Java",
            "framework": "Maven",
            "languages": ["Java"],
            "package_managers": ["maven"],
            "entry_points": [],
        }

    def _analyze_gradle(self, path: Path) -> Dict[str, Any]:
        return {
            "type": "Java",
            "framework": "Gradle",
            "languages": ["Java", "Kotlin"],
            "package_managers": ["gradle"],
            "entry_points": [],
        }

    def _analyze_composer(self, path: Path) -> Dict[str, Any]:
        return {
            "type": "PHP",
            "languages": ["PHP"],
            "package_managers": ["composer"],
            "entry_points": ["index.php"],
        }

    def _analyze_ruby(self, path: Path) -> Dict[str, Any]:
        return {
            "type": "Ruby",
            "languages": ["Ruby"],
            "package_managers": ["bundler"],
            "entry_points": [],
        }

    def _analyze_by_extensions(self) -> Dict[str, Any]:
        counts: Dict[str, int] = defaultdict(int)
        for fp in self._iter_project_files():
            counts[fp.suffix] += 1
        if not counts:
            return {"type": "Unknown", "languages": [], "entry_points": []}
        primary_ext = max(counts.items(), key=lambda kv: kv[1])[0]
        return {
            "type": SUPPORTED_EXTENSIONS[primary_ext],
            "languages": [SUPPORTED_EXTENSIONS[e] for e in counts],
            "entry_points": [],
        }

    def _find_python_entry_points(self) -> List[str]:
        names = ["main.py", "app.py", "run.py", "server.py", "manage.py", "cli.py"]
        found = [n for n in names if (self.project_path / n).exists()]
        src_main = self.project_path / "src" / "main.py"
        if src_main.exists():
            found.append(str(src_main.relative_to(self.project_path)))
        return found

    # -------------------------------------------------------- file analysis
    def analyze_file(self, file_path: Path) -> Optional[FileInfo]:
        """Analyze one source file; returns None on unreadable/binary files."""
        try:
            stat = file_path.stat()
            raw = file_path.read_bytes()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1")
                if "\x00" in content[:4000]:  # binary heuristic
                    return None

            ext = file_path.suffix.lower()
            language = SUPPORTED_EXTENSIONS.get(ext)
            if language is None:
                try:
                    language = get_lexer_for_filename(str(file_path)).name
                except ClassNotFound:
                    language = "Unknown"

            lines = content.count("\n") + (0 if content.endswith("\n") or not content else 1)
            code_lines = sum(1 for ln in content.splitlines() if ln.strip())

            # ---- unified deep analysis for every language ----------------
            parsed = parse_source(ext, language, content)
            functions = [f.name for f in parsed.functions_detail]
            classes = [c.name for c in parsed.classes_detail]
            imports = parsed.imports
            complexity_score = parsed.complexity
            docstring = parsed.docstring

            summary = self._generate_file_summary(file_path, language, functions, classes)

            return FileInfo(
                path=str(file_path.relative_to(self.project_path)),
                language=language,
                size=stat.st_size,
                lines=lines,
                functions=functions,
                classes=classes,
                imports=sorted(set(imports)),
                complexity_score=complexity_score,
                summary=summary,
                code_lines=code_lines,
                docstring=docstring[:300],
                functions_detail=parsed.functions_detail,
                classes_detail=parsed.classes_detail,
                todos=parsed.todos,
                endpoints=parsed.endpoints,
            )
        except Exception as e:  # never let one bad file kill the run
            self._log(f"Error analyzing {file_path}: {e}")
            return None

    def _generate_file_summary(
        self, file_path: Path, language: str, functions: List[str], classes: List[str]
    ) -> str:
        parts = [f"{language} module"]
        if classes:
            parts.append(f"defines class(es): {', '.join(classes[:3])}")
        if functions:
            parts.append(f"contains function(s): {', '.join(functions[:3])}")
        name = file_path.name.lower()
        role_hints = [
            ("test", "(testing module)"),
            ("util", "(utility module)"),
            ("helper", "(utility module)"),
            ("config", "(configuration)"),
            ("setting", "(configuration)"),
            ("model", "(data model)"),
            ("schema", "(data schema)"),
            ("controller", "(request handler)"),
            ("route", "(request handler)"),
            ("service", "(business logic)"),
            ("widget", "(UI component)"),
            ("component", "(UI component)"),
            ("view", "(UI component)"),
        ]
        for token, hint in role_hints:
            if token in name:
                parts.append(hint)
                break
        return " ".join(parts)

    # ------------------------------------------------------- project level
    def analyze_project(
        self,
        ai_api_key: Optional[str] = None,
        enable_complexity: bool = False,
        run_linters: bool = True,
    ) -> ProjectStructure:
        """Run the complete analysis pipeline and return ProjectStructure."""
        console.print("[bold cyan]🔍 Starting project analysis…[/]")
        started = time.time()

        project_info = self.detect_project_type()
        console.print(f"  ✓ Type: [bold]{project_info['type']}[/]"
                      + (f" | Framework: [bold]{project_info['framework']}[/]" if project_info["framework"] else ""))

        # ---- parallel per-file analysis ---------------------------------
        all_files = self._iter_project_files()
        files: List[FileInfo] = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Analyzing files…", total=len(all_files))
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {pool.submit(self.analyze_file, fp): fp for fp in all_files}
                for fut in as_completed(futures):
                    fi = fut.result()
                    if fi:
                        files.append(fi)
                    progress.update(task, advance=1)
        files.sort(key=lambda f: f.path)
        console.print(f"  ✓ Analyzed [bold]{len(files)}[/] files "
                      f"({sum(f.lines for f in files):,} lines)")

        dependencies = self._extract_dependencies()
        architecture = self._categorize_architecture(files)
        metrics = self._calculate_metrics(files)
        file_dep_graph = self._build_file_dependency_graph(files)

        abs_paths = {f.path: self.project_path / f.path for f in files}
        py_files = [abs_paths[f.path] for f in files if f.language == "Python"]
        js_files = [abs_paths[f.path] for f in files if f.language in ("JavaScript", "TypeScript")]

        # ---- optional heavy analyses ------------------------------------
        coverage_data = parse_coverage_xml(self.project_path / "coverage.xml")
        overall_coverage = get_overall_coverage(coverage_data) if coverage_data else None

        linting_results = flake8_results = eslint_results = None
        complexity_results = maintainability_results = security_results = None

        if run_linters:
            if py_files:
                with console.status("[yellow]Running pylint (batched)…", spinner="dots"):
                    linting_results = run_pylint_on_files(py_files)
                flake8_results = run_flake8_on_files(py_files)
            if js_files:
                with console.status("[yellow]Running eslint (batched)…", spinner="dots"):
                    eslint_results = run_eslint_on_files(js_files)

        if enable_complexity and py_files and tool_available("radon"):
            with console.status("[magenta]Running radon complexity (batched)…", spinner="dots"):
                complexity_results = analyze_complexity_with_radon(py_files)
                maintainability_results = analyze_maintainability_with_radon(py_files)

        if py_files:
            with console.status("[red]Running bandit security scan (batched)…", spinner="dots"):
                security_results = analyze_security_with_bandit(py_files)

        call_graph = extract_call_graph(py_files)
        cycles = find_cycles(call_graph)
        detected_frameworks = sorted(detect_frameworks(list(abs_paths.values())))
        contributors = get_contributors(self.project_path)
        git_stats = get_git_stats(self.project_path)

        ai_summaries: Dict[str, str] = {}
        if ai_api_key and py_files:
            with console.status("[green]Generating AI summaries…", spinner="dots"):
                for pf in py_files[:50]:  # cost guard: top 50 files max
                    s = ai_summarize_code(pf, ai_api_key)
                    if s:
                        ai_summaries[str(pf)] = s

        structure = ProjectStructure(
            name=self.project_path.name,
            type=project_info["type"],
            languages=project_info["languages"],
            entry_points=project_info["entry_points"],
            dependencies=dependencies,
            files=files,
            architecture=architecture,
            metrics=metrics,
            framework=project_info.get("framework"),
            package_managers=project_info.get("package_managers", []),
            file_dependency_graph=file_dep_graph,
            coverage=coverage_data,
            overall_coverage=overall_coverage,
            linting=linting_results,
            call_graph_cycles=cycles,
            detected_frameworks=detected_frameworks,
            contributors=contributors,
            git_stats=git_stats,
            flake8=flake8_results,
            eslint=eslint_results,
            complexity=complexity_results,
            maintainability=maintainability_results,
            security=security_results,
            ai_summaries=ai_summaries or None,
        )
        structure.health = compute_health_score(
            metrics=metrics,
            test_ratio=(len(architecture.get("Tests", [])) / len(files)) if files else 0,
            lint_issue_count=len(linting_results or []) + len(flake8_results or []),
            security_counts=_security_counts(security_results),
            overall_coverage=overall_coverage,
            avg_maintainability=_avg_maintainability(maintainability_results),
            documented_pct=metrics.get("documented_symbols_pct"),
        )
        self.project_structure = structure
        elapsed = time.time() - started
        console.print(f"  ✓ Analysis finished in [bold green]{elapsed:.1f}s[/]")
        return structure

    # ------------------------------------------------------------ helpers
    def _extract_dependencies(self) -> Dict[str, List[str]]:
        deps: Dict[str, List[str]] = {"runtime": [], "development": []}

        pkg = self.project_path / "package.json"
        if pkg.exists():
            data = self._read_json(pkg) or {}
            deps["runtime"].extend(sorted((data.get("dependencies") or {}).keys()))
            deps["development"].extend(sorted((data.get("devDependencies") or {}).keys()))

        req = self.project_path / "requirements.txt"
        if req.exists():
            try:
                for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        name = re.split(r"[<>=~!\[]", line)[0].strip()
                        if name:
                            deps["runtime"].append(name)
            except OSError:
                pass

        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                data = toml.load(pyproject)
                proj = data.get("project", {})
                for item in proj.get("dependencies", []) or []:
                    name = re.split(r"[<>=~!\[]", str(item))[0].strip()
                    if name and name not in deps["runtime"]:
                        deps["runtime"].append(name)
            except Exception:
                pass

        deps["runtime"] = sorted(set(deps["runtime"]))
        deps["development"] = sorted(set(deps["development"]))
        return deps

    def _categorize_architecture(self, files: List[FileInfo]) -> Dict[str, List[str]]:
        categories: Dict[str, List[str]] = {
            "Models": [], "Controllers": [], "Views": [], "Services": [],
            "Utils": [], "Tests": [], "Config": [], "Docs": [], "Other": [],
        }
        rules = [
            ("Tests", ("test", "spec")),
            ("Config", ("config", "setting", "env")),
            ("Models", ("model", "schema", "entity")),
            ("Controllers", ("controller", "route", "handler", "api")),
            ("Views", ("view", "component", "template", "screen", "page", "ui")),
            ("Services", ("service", "business", "logic", "engine", "manager")),
            ("Utils", ("util", "helper", "tool", "common")),
            ("Docs", ("doc", "readme", "guide")),
        ]
        for fi in files:
            lowered = fi.path.lower()
            placed = False
            for cat, tokens in rules:
                if any(t in lowered for t in tokens):
                    categories[cat].append(fi.path)
                    placed = True
                    break
            if not placed:
                categories["Other"].append(fi.path)
        return categories

    def _calculate_metrics(self, files: List[FileInfo]) -> Dict[str, Any]:
        total_files = len(files)
        total_lines = sum(f.lines for f in files)
        code_lines = sum(f.code_lines for f in files)
        lang_dist: Dict[str, int] = defaultdict(int)
        for fi in files:
            lang_dist[fi.language] += fi.lines

        largest = max(files, key=lambda f: f.lines).path if files else None

        # ---- deep-analysis aggregates ------------------------------------
        all_funcs = [(fi, fd) for fi in files for fd in fi.functions_detail]
        documented_syms = sum(1 for fi in files for fd in fi.functions_detail
                              if not fd.name.startswith("_") and fd.documented)
        public_syms = sum(1 for fi in files for fd in fi.functions_detail
                          if not fd.name.startswith("_"))
        doc_pct = round(100.0 * documented_syms / public_syms, 1) if public_syms else None

        long_functions = [
            {"file": fi.path, "name": fd.name, "complexity": fd.complexity, "args": fd.args}
            for fi, fd in all_fds_sorted(all_funcs)
            if fd.complexity >= 10 or fd.args > 5
        ][:15]

        endpoints = sorted({ep for fi in files for ep in fi.endpoints})
        total_todos = sum(fi.todos for fi in files)

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "code_lines": code_lines,
            "blank_comment_lines": total_lines - code_lines,
            "total_functions": sum(len(f.functions) for f in files),
            "total_classes": sum(len(f.classes) for f in files),
            "average_complexity": round(
                sum(f.complexity_score for f in files) / total_files, 2
            ) if total_files else 0,
            "language_distribution": dict(lang_dist),
            "largest_file": largest,
            "total_size_kb": round(sum(f.size for f in files) / 1024, 1),
            # intelligence layer
            "documented_symbols_pct": doc_pct,
            "total_todos": total_todos,
            "total_endpoints": len(endpoints),
            "avg_function_args": round(
                sum(fd.args for _, fd in all_funcs) / len(all_funcs), 2
            ) if all_funcs else 0,
            "complex_hotspots": long_functions,
        }

    def _build_file_dependency_graph(self, files: List[FileInfo]) -> Dict[str, List[str]]:
        """O(n·m) import graph using stem/dotted-module indexes."""
        by_stem: Dict[str, List[str]] = defaultdict(list)
        by_dotted: Dict[str, str] = {}
        for f in files:
            stem = Path(f.path).stem
            dotted = Path(f.path).with_suffix("").as_posix().replace("/", ".")
            by_stem[stem].append(f.path)
            by_dotted[dotted] = f.path

        graph: Dict[str, List[str]] = {f.path: [] for f in files}
        for f in files:
            seen: Set[str] = set()
            for imp in f.imports:
                parts = imp.split(".")
                target: Optional[str] = None
                for i in range(len(parts), 0, -1):
                    cand = ".".join(parts[:i])
                    if cand in by_dotted and by_dotted[cand] != f.path:
                        target = by_dotted[cand]
                        break
                if target is None and parts[0] in by_stem:
                    local = [p for p in by_stem[parts[0]] if p != f.path]
                    target = local[0] if local else None
                if target and target not in seen:
                    seen.add(target)
                    graph[f.path].append(target)
        return graph


def _security_counts(security: Optional[Dict[str, list]]) -> Dict[str, int]:
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for issues in (security or {}).values():
        for issue in issues:
            sev = str(issue.get("issue_severity", "LOW")).upper()
            counts[sev] = counts.get(sev, 0) + 1
    return counts


def all_fds_sorted(pairs):
    """Sort (FileInfo, FunctionInfo) pairs by complexity, hottest first."""
    return sorted(pairs, key=lambda p: p[1].complexity, reverse=True)


def _avg_maintainability(maintainability: Optional[Dict[str, Any]]) -> Optional[float]:
    """Average Maintainability Index across files (None when unavailable)."""
    if not maintainability:
        return None
    values = []
    for entry in maintainability.values():
        if isinstance(entry, dict):
            mi = entry.get("mi")
            if isinstance(mi, (int, float)):
                values.append(mi)
        elif isinstance(entry, (int, float)):
            values.append(entry)
    return round(sum(values) / len(values), 1) if values else None


def _project_endpoints(s: ProjectStructure) -> List[str]:
    """Deduplicated HTTP endpoint list across the whole project."""
    seen: List[str] = []
    for fi in s.files:
        for ep in fi.endpoints:
            if ep not in seen:
                seen.append(ep)
    return seen[:120]


# ---------------------------------------------------------------------------
# Documentation generation
# ---------------------------------------------------------------------------


class DocumentationGenerator:
    """Generates every documentation artifact into the output directory."""

    def __init__(
        self,
        project_structure: ProjectStructure,
        output_dir: Path,
        project_root: Optional[Path] = None,
    ):
        self.structure = project_structure
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_root = Path(project_root) if project_root else None
        self.generated: List[str] = []

    def _src(self, rel_path: str) -> Path:
        """Resolve a relative file path against the real project root."""
        base = self.project_root or self.structure_root_fallback()
        return base / rel_path

    def structure_root_fallback(self) -> Path:
        # legacy behavior: assume output sits inside the project
        return self.output_dir.parent

    # ------------------------------------------------------------------ all
    def generate_all(self) -> List[str]:
        console.print("[bold cyan]📝 Generating documentation…[/]")
        self.generate_enhanced_readme()
        self.generate_architecture_diagram()
        self.generate_file_dependency_diagram()
        self.generate_ai_summary()
        self.generate_prompt_ready()
        self.generate_uml_diagram()
        self.generate_usage_examples_file()
        self.generate_file_summaries()
        self.write_quality_reports()
        self.write_recommendations()
        self.generate_html_report()
        console.print(f"  ✓ Generated [bold]{len(self.generated)}[/] artifacts in "
                      f"[bold]{self.output_dir}[/]")
        return self.generated

    def _write(self, filename: str, content: str, binary: bool = False):
        mode = "wb" if binary else "w"
        enc = {} if binary else {"encoding": "utf-8"}
        with open(self.output_dir / filename, mode, **enc) as f:
            f.write(content)
        self.generated.append(filename)

    # --------------------------------------------------------------- README
    def generate_enhanced_readme(self):
        s = self.structure
        cov = f"{s.overall_coverage:.1f}%" if s.overall_coverage is not None else "Not available"
        lint_n = len(s.linting or [])
        health = s.health or {}
        description = generate_project_description(s)
        badges = " ".join([
            f"![Language](https://img.shields.io/badge/language-{s.type.replace(' ', '%20')}-blue)",
            f"![Files](https://img.shields.io/badge/files-{s.metrics['total_files']}-informational)",
            f"![Lines](https://img.shields.io/badge/lines-{s.metrics['total_lines']:,}-informational)",
            f"![Health](https://img.shields.io/badge/health-{health.get('grade','?')}-{_health_color(health.get('score', 0))})",
        ])
        content = f"""# {s.name}

{badges}

## 🚀 Overview
{description}

## 📊 Project Statistics
| Metric | Value |
|---|---|
| Type | {s.type} |
| Languages | {', '.join(s.languages)} |
| Files | {s.metrics['total_files']} |
| Total Lines | {s.metrics['total_lines']:,} |
| Code Lines | {s.metrics['code_lines']:,} |
| Functions | {s.metrics['total_functions']} |
| Classes | {s.metrics['total_classes']} |
| Avg Complexity | {s.metrics['average_complexity']} |
| Test Coverage | {cov} |
| Lint Issues | {lint_n} |
| Health Score | {health.get('score', '—')}/100 ({health.get('grade', '—')}) |

### 📂 Project Structure
```text
{_ascii_tree(s.architecture)}
```

{generate_structure_description(s)}

## 🔧 Dependencies
{generate_dependencies_section(s)}

## 🚀 Getting Started

### Prerequisites
{generate_prerequisites(s)}

### Installation
{generate_installation_steps(s)}

### Usage
{generate_usage_examples_block(s)}

## 🏥 Health Report
{generate_health_section(s)}

## 📈 Language Distribution
{format_language_distribution(s)}

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---
*This README was auto-generated by SmartRepo Analyzer v{__version__} at {utc_now_iso()}*
"""
        self._write("readme-enhanced.md", content)

    # ------------------------------------------------------------ diagrams
    def generate_architecture_diagram(self):
        mermaid_content = _mermaid_architecture(self.structure)
        self._write("architecture.mmd", mermaid_content)
        self._render_png("architecture.mmd", "architecture.png")

    def _render_png(self, mmd_name: str, png_name: str):
        from tool_runner import tool_path
        mmdc = tool_path("mmdc")
        if not mmdc:
            console.print("  ⚠ mermaid-cli not found — PNG rendering skipped "
                          "(npm i -g @mermaid-js/mermaid-cli)")
            return
        try:
            result = subprocess.run(
                [mmdc, "-i", str(self.output_dir / mmd_name),
                 "-o", str(self.output_dir / png_name), "-t", "neutral", "-b", "white"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and png_name:
                self.generated.append(png_name)
                console.print(f"  ✓ {png_name} rendered")
        except (subprocess.TimeoutExpired, OSError):
            pass

    def generate_file_dependency_diagram(self):
        g = self.structure.file_dependency_graph or {}
        if not any(g.values()):
            return
        lines = ["graph TD"]
        edges = 0
        for src, targets in sorted(g.items()):
            for tgt in targets[:20]:  # keep diagrams readable
                lines.append(f"    {_mid(src)}['{Path(src).name}'] --> {_mid(tgt)}['{Path(tgt).name}']")
                edges += 1
        if edges > 800:
            return  # too dense to be useful
        self._write("file-dependency-graph.mmd", "\n".join(lines))

    # ------------------------------------------------------------ summaries
    def generate_ai_summary(self):
        s = self.structure
        summary = {
            "project_overview": {
                "name": s.name,
                "type": s.type,
                "framework": s.framework,
                "languages": s.languages,
                "entry_points": s.entry_points,
                "detected_frameworks": s.detected_frameworks,
                "description": generate_project_description(s),
            },
            "health": s.health,
            "git": s.git_stats,
            "metrics": s.metrics,
            "dependencies": s.dependencies,
            "architecture": {
                category: {
                    "file_count": len(files_),
                    "files": files_,
                    "description": CATEGORY_DESCRIPTIONS.get(category, "Project files"),
                }
                for category, files_ in s.architecture.items() if files_
            },
            "file_summaries": [
                {
                    "path": f.path,
                    "language": f.language,
                    "summary": f.summary,
                    "docstring": f.docstring,
                    "functions": f.functions[:15],
                    "classes": f.classes,
                    "lines": f.lines,
                    "code_lines": f.code_lines,
                    "complexity": f.complexity_score,
                    "documented_pct": round(f.documented_pct, 1),
                    "todos": f.todos,
                }
                for f in sorted(s.files, key=lambda x: x.lines, reverse=True)[:30]
            ],
            "code_intelligence": {
                "endpoints": _project_endpoints(s),
                "complex_hotspots": s.metrics.get("complex_hotspots", []),
                "documented_symbols_pct": s.metrics.get("documented_symbols_pct"),
                "total_todos": s.metrics.get("total_todos", 0),
                "avg_function_args": s.metrics.get("avg_function_args", 0),
                "top_classes": [
                    {
                        "file": f.path,
                        "name": c.name,
                        "kind": c.kind,
                        "bases": c.bases,
                        "methods": len(c.methods) if c.methods else None,
                    }
                    for f in s.files
                    for c in f.classes_detail[:8]
                ][:40],
                "public_api_surface": [
                    {"file": fi.path, "name": fd.name, "args": fd.args}
                    for fi in s.files
                    for fd in fi.functions_detail
                    if fd.exported
                ][:80],
            },
            "call_graph_cycles": s.call_graph_cycles,
            "key_insights": generate_key_insights(s),
            "generated_at": s.generated_at,
            "analyzer_version": ANALYZER_VERSION,
        }
        self._write("ai-summary.json", json.dumps(summary, indent=2, ensure_ascii=False))

    def generate_prompt_ready(self):
        s = self.structure
        health = s.health or {}
        complexity_level = (
            "High" if s.metrics["average_complexity"] > 5
            else "Medium" if s.metrics["average_complexity"] > 3 else "Low"
        )
        content = f"""# AI-Ready Project Analysis: {s.name}

## Quick Summary
This is a **{s.type}** project ({s.framework or 'no dominant framework'}) with \
{s.metrics['total_files']} files and {s.metrics['total_lines']:,} lines of code across \
{len(s.languages)} language(s). Health score: **{health.get('score', '—')}/100 ({health.get('grade', '—')})**.

## Project Context
- **Type**: {s.type}
- **Framework**: {s.framework or 'Not detected'}
- **Languages**: {', '.join(s.languages)}
- **Entry Points**: {', '.join(s.entry_points) if s.entry_points else 'Not specified'}
- **Detected Frameworks**: {', '.join(s.detected_frameworks or []) or 'None'}
- **Package Managers**: {', '.join(s.package_managers) or 'Unknown'}

## Architecture Overview
{prompt_architecture_section(s)}

## Key Components
{components_prompt_section(s)}

## Code Characteristics
- **Complexity Level**: {complexity_level} (avg {s.metrics['average_complexity']})
- **Total Functions**: {s.metrics['total_functions']}
- **Total Classes**: {s.metrics['total_classes']}
- **Testing**: {'Well-tested' if s.architecture.get('Tests') else 'Limited testing'}
- **Documentation**: {s.metrics.get('documented_symbols_pct', '—')}% of public symbols documented
- **TODO/FIXME markers**: {s.metrics.get('total_todos', 0)}

## HTTP API Surface
{endpoints_prompt_section(s)}

## Complexity Hotspots (refactor candidates)
{hotspots_prompt_section(s)}

## Dependencies Context
{dependencies_prompt_section(s)}

## Development Insights
{chr(10).join('- ' + i for i in generate_key_insights(s))}

## Language Distribution
{language_prompt_section(s)}

---
*Generated by SmartRepo Analyzer v{__version__} — ready-to-use context for LLMs.*
"""
        self._write("prompt-ready.md", content)

    def generate_uml_diagram(self):
        py_files = [self._src(f.path) for f in self.structure.files if f.language == "Python"]
        if py_files:
            out = self.output_dir / "uml-class-diagram.mmd"
            generate_mermaid_class_diagram(py_files, out)
            self.generated.append("uml-class-diagram.mmd")

    def generate_usage_examples_file(self):
        py_files = [self._src(f.path) for f in self.structure.files if f.language == "Python"]
        examples = extract_usage_examples(py_files)
        if examples:
            self._write("usage-examples.txt", "\n".join(examples))

    def generate_file_summaries(self):
        summaries_dir = self.output_dir / "summaries"
        count = 0
        for f in self.structure.files:
            if f.lines <= 150:
                continue
            src = self._src(f.path)
            if src.exists():
                summaries_dir.mkdir(exist_ok=True)
                safe = str(f.path).replace(os.sep, "__")
                (summaries_dir / f"summary_{safe}.txt").write_text(
                    summarize_file(src), encoding="utf-8"
                )
                count += 1
        if count:
            self.generated.append("summaries/")
            console.print(f"  ✓ Summarized {count} large files")

    def write_quality_reports(self):
        s = self.structure
        dumps = {
            "flake8-linting.json": s.flake8,
            "eslint-linting.json": s.eslint,
            "complexity_report.json": s.complexity,
            "maintainability_report.json": s.maintainability,
            "security_report.json": s.security,
            "coverage.json": s.coverage,
        }
        for name, data in dumps.items():
            if data:
                self._write(name, json.dumps(data, indent=2, ensure_ascii=False, default=str))
        if s.call_graph_cycles:
            text = "\n".join(" -> ".join(c) for c in s.call_graph_cycles)
            self._write("call-graph-cycles.txt", text)
        if s.contributors:
            lines = [f"{c['name']}: {c['commits']} commits" for c in s.contributors]
            if s.git_stats and s.git_stats.get("total_commits"):
                lines.append(f"\nTotal commits: {s.git_stats['total_commits']}")
                lines.append(f"Last commit: {s.git_stats.get('last_commit', '?')}")
            self._write("contributors.txt", "\n".join(lines))

    def write_recommendations(self):
        s = self.structure
        recs = generate_recommendations(
            s.metrics,
            coverage=s.overall_coverage,
            lint_issues=(len(s.linting or []) + len(s.flake8 or [])),
            security_issues=_security_counts(s.security),
            test_ratio=(
                len(s.architecture.get("Tests", [])) / s.metrics["total_files"]
                if s.metrics["total_files"] else 0
            ),
        )
        header = (
            f"# Recommendations — health {s.health['score']}/100 ({s.health['grade']})\n\n"
            + "\n".join(recs)
        ) if s.health else "\n".join(recs)
        self._write("recommendations.txt", header)

    # -------------------------------------------------------------- report
    def generate_html_report(self):
        s = self.structure
        health = s.health or {"score": "—", "grade": "?"}
        color = _health_color(health.get("score", 0))
        lang_rows = "".join(
            f"<tr><td>{lang}</td><td>{n:,}</td><td>"
            f"<div style='background:#2563eb;height:14px;width:{pct:.0f}px'></div></td></tr>"
            for lang, n in _top_languages(s)[:15]
            for pct in [_lang_pct(s, lang)]
        )
        insight_items = "".join(f"<li>{i}</li>" for i in generate_key_insights(s))
        rec_items = ""
        endpoints = _project_endpoints(s)
        endpoint_rows = "".join(f"<tr><td><code>{ep}</code></td></tr>" for ep in endpoints[:60])
        hotspot_rows = "".join(
            f"<tr><td><code>{h['name']}</code></td><td>{h['file']}</td>"
            f"<td>{h['complexity']}</td><td>{h.get('args', 0)}</td></tr>"
            for h in (s.metrics.get("complex_hotspots") or [])[:10]
        )
        html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{s.name} — SmartRepo Report</title>
<style>
 body{{font-family:'Segoe UI',system-ui,sans-serif;margin:0;background:#f8fafc;color:#1e293b}}
 .wrap{{max-width:960px;margin:2rem auto;padding:0 1rem}}
 h1{{margin-bottom:0}} .sub{{color:#64748b}}
 .cards{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}}
 .card{{flex:1;min-width:140px;background:#fff;border-radius:12px;padding:16px;
       box-shadow:0 1px 3px rgba(0,0,0,.08);text-align:center}}
 .card b{{font-size:26px;display:block}} .badge{{font-size:42px;font-weight:800;color:{color}}}
 table{{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden}}
 td,th{{padding:8px 12px;border-bottom:1px solid #e2e8f0;text-align:left;font-size:14px}}
 section{{background:#fff;border-radius:12px;padding:20px;margin:16px 0;
         box-shadow:0 1px 3px rgba(0,0,0,.06)}}
 footer{{text-align:center;color:#94a3b8;padding:24px;font-size:13px}}
</style></head><body><div class="wrap">
<h1>{s.name}</h1>
<p class="sub">{s.type}{(' · ' + s.framework) if s.framework else ''} ·
generated {s.generated_at} · SmartRepo v{__version__}</p>

<section><div class="cards">
 <div class="card"><span class="badge">{health.get('score','—')}</span>Health Score<br>({health.get('grade','—')})</div>
 <div class="card"><b>{s.metrics['total_files']}</b>Files</div>
 <div class="card"><b>{s.metrics['total_lines']:,}</b>Lines</div>
 <div class="card"><b>{s.metrics['total_functions']}</b>Functions</div>
 <div class="card"><b>{s.metrics['average_complexity']}</b>Avg Complexity</div>
</div></section>

<section><h2>🗣 Language Distribution</h2>
<table><tr><th>Language</th><th>Lines</th><th></th></tr>{lang_rows}</table></section>

<section><h2>💡 Key Insights</h2><ul>{insight_items}</ul></section>
{f'<section><h2>🛣️ API Endpoints ({len(endpoints)})</h2><table><tr><th>Method &amp; Path</th></tr>{endpoint_rows}</table></section>' if endpoints else ''}
{f'<section><h2>🔥 Complexity Hotspots</h2><table><tr><th>Function</th><th>File</th><th>Complexity</th><th>Args</th></tr>{hotspot_rows}</table></section>' if hotspot_rows else ''}
<footer>Auto-generated by SmartRepo Analyzer — github.com/ALSRKAL/smartrepo-analyzer</footer>
</div></body></html>"""
        self._write("report.html", html)


# --------------------------------------------------------------------------
# Module-level pure helpers (unit-testable, used by DocumentationGenerator)
# --------------------------------------------------------------------------

CATEGORY_DESCRIPTIONS = {
    "Models": "Data models, schemas, and database entities",
    "Controllers": "Request handlers, route controllers, and API endpoints",
    "Views": "UI components, templates, and presentation layer",
    "Services": "Business logic, services, and core functionality",
    "Utils": "Utility functions, helpers, and common tools",
    "Tests": "Test suites, unit tests, and testing utilities",
    "Config": "Configuration files and environment settings",
    "Docs": "Documentation assets",
    "Other": "Miscellaneous files and additional components",
}


def _health_color(score) -> str:
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "#64748b"
    if score >= 80:
        return "#16a34a"
    if score >= 60:
        return "#d97706"
    return "#dc2626"


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def _mid(path: str) -> str:
    return "N_" + re.sub(r"[^A-Za-z0-9_]", "_", path)


def _ascii_tree(architecture: Dict[str, List[str]]) -> str:
    lines: List[str] = []
    for category, files in architecture.items():
        if not files:
            continue
        lines.append(f"{'├──' if lines else '┌──'} {category}/ ({len(files)})")
        for i, fp in enumerate(files[:8]):
            prefix = "│   ├──" if i < min(len(files), 8) - 1 else "│   └──"
            lines.append(f"{prefix} {Path(fp).name}")
        if len(files) > 8:
            lines.append("│   └── … and more")
    return "\n".join(lines)


def _top_languages(s: ProjectStructure) -> List[Tuple[str, int]]:
    dist = s.metrics.get("language_distribution", {})
    return sorted(dist.items(), key=lambda kv: kv[1], reverse=True)


def _lang_pct(s: ProjectStructure, lang: str) -> float:
    dist = s.metrics.get("language_distribution", {})
    total = sum(dist.values()) or 1
    return dist.get(lang, 0) / total * 200


def generate_project_description(s: ProjectStructure) -> str:
    desc = f"A {s.type} application"
    if s.framework:
        desc += f" built with {s.framework}"
    mains = [f for f in s.files if any(f.path == ep or f.path.endswith(ep) for ep in s.entry_points)]
    if mains:
        desc += f", with its main entry point at `{mains[0].path}`"
    arch = s.architecture
    if arch.get("Models"):
        desc += ", featuring a structured data layer"
    if arch.get("Services"):
        desc += " and dedicated business-logic services"
    if arch.get("Tests"):
        desc += f". The project includes {len(arch['Tests'])} test file(s)"
    return desc + "."


def generate_structure_description(s: ProjectStructure) -> str:
    out = ["### Layer Breakdown", ""]
    for category, files in s.architecture.items():
        if files:
            out.append(f"- **{category}** ({len(files)}): {CATEGORY_DESCRIPTIONS[category]}")
    return "\n".join(out)


def generate_dependencies_section(s: ProjectStructure) -> str:
    sections = []
    if s.dependencies.get("runtime"):
        sections.append("### Runtime Dependencies")
        sections += [f"- `{d}`" for d in s.dependencies["runtime"][:12]]
        if len(s.dependencies["runtime"]) > 12:
            sections.append(f"- … and {len(s.dependencies['runtime']) - 12} more")
    if s.dependencies.get("development"):
        sections.append("\n### Development Dependencies")
        sections += [f"- `{d}`" for d in s.dependencies["development"][:8]]
    return "\n".join(sections) if sections else "No dependency manifests detected."


def generate_prerequisites(s: ProjectStructure) -> str:
    table = {
        "Node.js": ["- Node.js ≥ 16", "- npm / yarn / pnpm"],
        "Python": ["- Python 3.8+", "- pip"],
        "Flutter": ["- Flutter SDK", "- Dart SDK"],
        "Rust": ["- Rust toolchain", "- Cargo"],
        "Go": ["- Go 1.19+"],
        "Java": ["- JDK 11+", "- Maven or Gradle"],
        "PHP": ["- PHP 8+", "- Composer"],
        "Ruby": ["- Ruby 3+", "- Bundler"],
    }
    return "\n".join(table.get(s.type, ["- See project documentation for requirements"]))


def generate_installation_steps(s: ProjectStructure) -> str:
    steps = ["```bash", f"git clone <repository-url>", f"cd {s.name}", ""]
    cmds = {
        "Node.js": ["npm install"],
        "Python": ["python -m venv venv && source venv/bin/activate", "pip install -r requirements.txt"],
        "Flutter": ["flutter pub get"],
        "Rust": ["cargo build --release"],
        "Go": ["go mod download"],
        "Java": ["mvn install"],
        "PHP": ["composer install"],
        "Ruby": ["bundle install"],
    }
    steps.extend(cmds.get(s.type, []))
    steps.append("```")
    return "\n".join(steps)


def generate_usage_examples_block(s: ProjectStructure) -> str:
    ex = ["```bash"]
    ep = s.entry_points[0] if s.entry_points else None
    starters = {
        "Node.js": ["npm start"],
        "Python": [f"python {ep}" if ep else "python -m <package>"],
        "Flutter": ["flutter run"],
        "Rust": ["cargo run"],
        "Go": [f"go run {ep}" if ep else "go run ."],
        "Java": ["mvn exec:java"],
    }
    ex.extend(starters.get(s.type, ["# See project documentation"]))
    ex.append("```")
    return "\n".join(ex)


def generate_health_section(s: ProjectStructure) -> str:
    h = s.health
    if not h:
        return "_Health analysis unavailable._"
    rows = "\n".join(f"| {k.title()} | {v} |" for k, v in h.get("breakdown", {}).items())
    return f"**Score: {h['score']}/100 — Grade {h['grade']}**\n\n| Factor | Status |\n|---|---|\n{rows}"


def format_language_distribution(s: ProjectStructure) -> str:
    total = sum(s.metrics.get("language_distribution", {}).values()) or 1
    lines = []
    for lang, n in _top_languages(s):
        pct = n / total * 100
        bar = "█" * max(int(pct // 5), 1)
        lines.append(f"- **{lang}**: {n:,} lines ({pct:.1f}%) {bar}")
    return "\n".join(lines) or "No data."


def generate_key_insights(s: ProjectStructure) -> List[str]:
    insights: List[str] = []
    m = s.metrics
    if m["average_complexity"] > 5:
        insights.append("High average complexity — refactoring the most complex modules will pay off.")
    elif m["average_complexity"] < 2:
        insights.append("Low-complexity, well-structured codebase.")

    # ---- intelligence layer --------------------------------------------
    hotspots = m.get("complex_hotspots") or []
    if hotspots:
        worst = hotspots[0]
        insights.append(
            f"Top complexity hotspot: `{worst['name']}` ({worst['file']}, complexity {worst['complexity']})."
        )
        too_many_args = [h for h in hotspots if h.get("args", 0) > 5]
        if too_many_args:
            insights.append(f"{len(too_many_args)} function(s) take more than 5 parameters — consider parameter objects.")

    doc_pct = m.get("documented_symbols_pct")
    if doc_pct is not None:
        if doc_pct >= 60:
            insights.append(f"Good documentation coverage: {doc_pct:.0f}% of public symbols documented.")
        elif doc_pct < 20:
            insights.append(f"Only {doc_pct:.0f}% of public symbols are documented — adding docstrings would help a lot.")

    todos = m.get("total_todos") or 0
    if todos > 50:
        insights.append(f"{todos} TODO/FIXME markers — schedule a cleanup sprint.")
    elif todos > 0:
        insights.append(f"{todos} TODO/FIXME marker(s) tracked in reports.")

    endpoints = m.get("total_endpoints") or 0
    if endpoints:
        insights.append(f"HTTP API surface detected: {endpoints} endpoint(s) mapped in the report.")

    tests = s.architecture.get("Tests", [])
    if m["total_files"]:
        ratio = len(tests) / m["total_files"]
        if ratio > 0.3:
            insights.append("Strong testing culture (>30% of files are tests).")
        elif ratio < 0.1 and s.architecture.get("Other") is not None:
            insights.append("Few test files detected — consider expanding unit/integration tests.")

    if s.architecture.get("Models") and s.architecture.get("Controllers"):
        insights.append("Follows an MVC-like layered architecture.")
    if s.architecture.get("Services"):
        insights.append("Service-oriented design detected.")

    if len(m.get("language_distribution", {})) >= 3:
        insights.append(f"Polyglot project spanning {len(m['language_distribution'])} languages.")

    if m["total_lines"] > 20000:
        insights.append("Large codebase — modularization would ease maintenance.")
    elif 0 < m["total_lines"] < 1000:
        insights.append("Compact project — easy to onboard new contributors.")

    if s.overall_coverage is not None:
        insights.append(f"Measured test coverage: {s.overall_coverage:.1f}%.")

    cycles = s.call_graph_cycles or []
    if cycles:
        insights.append(f"{len(cycles)} circular call chain(s) detected — review callgraph cycles report.")

    sec = _security_counts(s.security)
    if sec.get("HIGH"):
        insights.append(f"⚠ {sec['HIGH']} high-severity security finding(s) need attention.")
    return insights or ["No significant issues detected."]


def prompt_architecture_section(s: ProjectStructure) -> str:
    return "\n".join(
        f"- **{cat}** ({len(fs)} files): {CATEGORY_DESCRIPTIONS.get(cat, '')}"
        for cat, fs in s.architecture.items() if fs
    )


def components_prompt_section(s: ProjectStructure) -> str:
    comps = ["**Largest files:**"]
    for f in sorted(s.files, key=lambda x: x.lines, reverse=True)[:5]:
        comps.append(f"- `{f.path}` ({f.lines} ln, {f.language}): {f.summary}")
    most_complex = sorted(s.files, key=lambda x: x.complexity_score, reverse=True)[:3]
    if most_complex and most_complex[0].complexity_score > 3:
        comps.append("\n**Most complex files:**")
        comps += [f"- `{f.path}` (complexity {f.complexity_score}): {f.summary}" for f in most_complex if f.complexity_score > 3]
    return "\n".join(comps)


def dependencies_prompt_section(s: ProjectStructure) -> str:
    secs = []
    if s.dependencies.get("runtime"):
        secs.append("**Key runtime dependencies**: " + ", ".join(s.dependencies["runtime"][:10]))
    if s.dependencies.get("development"):
        secs.append("**Dev tools**: " + ", ".join(s.dependencies["development"][:6]))
    return "\n".join(secs) if secs else "No major dependencies detected."


def endpoints_prompt_section(s: ProjectStructure) -> str:
    endpoints = _project_endpoints(s)
    if not endpoints:
        return "_No HTTP endpoints detected._"
    return "\n".join(f"- `{ep}`" for ep in endpoints[:40])


def hotspots_prompt_section(s: ProjectStructure) -> str:
    hotspots = s.metrics.get("complex_hotspots") or []
    if not hotspots:
        return "_No significant complexity hotspots detected._"
    return "\n".join(
        f"- `{h['name']}` in `{h['file']}` — complexity {h['complexity']}, {h.get('args', 0)} arg(s)"
        for h in hotspots
    )


def language_prompt_section(s: ProjectStructure) -> str:
    total = sum(s.metrics.get("language_distribution", {}).values()) or 1
    return "\n".join(
        f"- **{lang}**: {n / total * 100:.1f}% ({n:,} lines)"
        for lang, n in _top_languages(s)
    )


def _mermaid_architecture(s: ProjectStructure) -> str:
    lines = ["graph TD"]
    node_id = 0
    lines.append(f"    APP[\"{s.name}\"]")
    MAX_FILES_PER_CATEGORY = 12
    for category, files in s.architecture.items():
        if not files:
            continue
        node_id += 1
        cat_node = f"CAT{node_id}"
        cls = {"Controllers": "controller", "Models": "model", "Views": "view",
               "Services": "service", "Tests": "test"}.get(category, "")
        suffix = f":::{cls}" if cls else ""
        lines.append(f'    {cat_node}["{category}"]{suffix}')
        lines.append(f"    APP --> {cat_node}")
        for fp in files[:MAX_FILES_PER_CATEGORY]:
            node_id += 1
            lines.append(f'    F{node_id}["{Path(fp).name}"]')
            lines.append(f"    {cat_node} --> F{node_id}")
        if len(files) > MAX_FILES_PER_CATEGORY:
            node_id += 1
            lines.append(f'    F{node_id}["… +{len(files) - MAX_FILES_PER_CATEGORY} more"]')
            lines.append(f"    {cat_node} --> F{node_id}")
    lines += [
        "",
        "    classDef controller fill:#e1f5fe,stroke:#0288d1",
        "    classDef model fill:#f3e5f5,stroke:#7b1fa2",
        "    classDef view fill:#e8f5e9,stroke:#388e3c",
        "    classDef service fill:#fff3e0,stroke:#f57c00",
        "    classDef test fill:#fce4ec,stroke:#c2185b",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class SmartRepoAnalyzer:
    """High-level application facade."""

    def __init__(self):
        self.version = __version__
        self.console = console

    def print_logo(self, quiet: bool = False):
        if quiet:
            return
        logo = """
███████╗███╗   ███╗ █████╗ ██████╗ ██████╗ ██████╗  ██████╗
██╔════╝████╗ ████║██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔═══██╗
███████╗██╔████╔██║███████║██████╔╝██████╔╝██║   ██║██████╔╝
╚════██║██║╚██╔╝██║██╔══██║██╔═══╝ ██╔══██╗██║   ██║██╔══██╗
███████║██║ ╚═╝ ██║██║  ██║██║     ██║  ██║╚██████╔╝██║  ██║
╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
"""
        panel = Panel.fit(
            f"[bold blue]{logo}[/]\n"
            f"🤖 [bold green]AI-Powered Code Analysis[/] ⚡   v{self.version}\n"
            "[dim]by alsrkal — github.com/ALSRKAL/smartrepo-analyzer[/]",
            title="[bold yellow]Welcome to SmartRepo[/]",
            border_style="magenta",
            box=box.DOUBLE,
        )
        self.console.print(panel, justify="center")

    def run(
        self,
        project_path: str,
        output_dir: Optional[str] = None,
        enable_complexity: bool = False,
        ai_api_key: Optional[str] = None,
        exclude: Optional[List[str]] = None,
        include: Optional[List[str]] = None,
        run_linters: bool = True,
        quiet: bool = False,
        verbose: bool = False,
    ) -> Optional[ProjectStructure]:
        """Analyze ``project_path`` and generate documentation. Returns structure."""
        self.print_logo(quiet=quiet)
        resolved = Path(project_path).resolve()
        if not resolved.exists():
            console.print(f"[bold red]❌ Error:[/] project path '{project_path}' does not exist")
            return None
        output_path = Path(output_dir).resolve() if output_dir else resolved / "smartrepo-analysis"

        try:
            subprojects = find_subprojects(resolved)
            if subprojects:
                console.print(f"[cyan]🔎 Monorepo detected — {len(subprojects)} subproject(s)[/]")
                for sub in subprojects:
                    console.rule(f"[bold]{sub.name}")
                    sub_out = output_path / sub.name
                    analyzer = CodeAnalyzer(
                        str(sub), exclude_patterns=exclude, include_patterns=include,
                        verbose=verbose,
                    )
                    structure = analyzer.analyze_project(
                        ai_api_key=ai_api_key,
                        enable_complexity=enable_complexity,
                        run_linters=run_linters,
                    )
                    DocumentationGenerator(structure, sub_out, project_root=sub).generate_all()
                    self._print_summary(structure, sub_out)
                console.print(f"\n🎉 All subproject analyses saved to: {output_path}")
                return None

            analyzer = CodeAnalyzer(
                str(resolved), exclude_patterns=exclude,
                include_patterns=include, verbose=verbose,
            )
            structure = analyzer.analyze_project(
                ai_api_key=ai_api_key,
                enable_complexity=enable_complexity,
                run_linters=run_linters,
            )
            DocumentationGenerator(structure, output_path, project_root=resolved).generate_all()
            self._print_summary(structure, output_path)
            return structure
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Interrupted by user[/]")
            return None
        except Exception as e:
            console.print(f"[bold red]❌ Error during analysis:[/] {e}")
            if verbose:
                console.print_exception()
            return None

    def _print_summary(self, structure: ProjectStructure, output_path: Path):
        h = structure.health or {}
        table = Table(title=f"📊 Analysis Complete — {structure.name}",
                      box=box.ROUNDED, show_header=False)
        table.add_column(style="bold cyan", width=22)
        table.add_column(style="white")
        table.add_row("Type", f"{structure.type}" + (f" · {structure.framework}" if structure.framework else ""))
        table.add_row("Languages", ", ".join(structure.languages))
        table.add_row("Files / Lines", f"{structure.metrics['total_files']} / {structure.metrics['total_lines']:,}")
        table.add_row("Functions / Classes",
                      f"{structure.metrics['total_functions']} / {structure.metrics['total_classes']}")
        table.add_row("Avg Complexity", str(structure.metrics["average_complexity"]))
        if h:
            color = "green" if h["score"] >= 80 else "yellow" if h["score"] >= 55 else "red"
            table.add_row("Health Score", f"[{color}]{h['score']}/100 ({h['grade']})[/]")
        if structure.overall_coverage is not None:
            table.add_row("Test Coverage", f"{structure.overall_coverage:.1f}%")
        sec = _security_counts(structure.security)
        if sec and (sec["HIGH"] or sec["MEDIUM"]):
            table.add_row("Security", f"{sec['HIGH']} high · {sec['MEDIUM']} medium")
        self.console.print(table)

        files_list = Table(box=box.SIMPLE, show_header=False)
        files_list.add_column(style="green")
        files_list.add_column(style="dim")
        key_outputs = [
            "readme-enhanced.md", "report.html", "ai-summary.json",
            "prompt-ready.md", "recommendations.txt",
        ]
        for name in key_outputs:
            fp = output_path / name
            if fp.exists():
                files_list.add_row(f"  ✓ {name}", f"{fp.stat().st_size:,} bytes")
            else:
                files_list.add_row(f"  ⚠ {name}", "not generated")
        self.console.print(files_list)
        self.console.print(f"📁 All outputs: [underline]{output_path}[/]\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

REQUIREMENTS_CONTENT = """# SmartRepo Analyzer requirements
rich>=13.0
pygments>=2.15
pyyaml>=6.0
toml>=0.10.2
networkx>=3.0        # optional: better cycle detection (pure-python fallback exists)
# Optional extras:
# openai>=1.0        # --ai-key smart summarization
# radon              # --complexity analysis
# bandit             # security scan
# pylint, flake8     # python linting
# eslint             # JS/TS linting (npm)
# pillow             # GUI image support
"""


def create_requirements_txt(path: str = "requirements.txt"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(REQUIREMENTS_CONTENT)
    console.print(f"📝 [green]'{path}' created[/]")


def launch_gui():
    """Start the desktop GUI, failing gracefully when unavailable."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from gui.main import MainApp
    except ImportError as e:
        console.print(f"[bold red]GUI unavailable:[/] {e}")
        console.print("Install GUI requirements: pip install pillow markdown")
        sys.exit(1)
    app = MainApp()
    app.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smartrepo_analyzer",
        description="SmartRepo Analyzer — AI-Powered Code Analysis & Documentation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python smartrepo_analyzer.py analyze ./my-project
  python smartrepo_analyzer.py analyze . --complexity --exclude "*.min.js" "dist/*"
  python smartrepo_analyzer.py analyze ./proj --ai-key sk-... -o ./analysis
  python smartrepo_analyzer.py gui
""",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    ap = sub.add_parser("analyze", help="Analyze a code project and generate reports")
    ap.add_argument("project_path", help="Path to the project directory")
    ap.add_argument("-o", "--output", help="Custom output directory")
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose diagnostics")
    ap.add_argument("-q", "--quiet", action="store_true", help="Hide banner/logo output")
    ap.add_argument("--complexity", action="store_true",
                    help="Enable detailed complexity/maintainability analysis (radon)")
    ap.add_argument("--no-lint", action="store_true", help="Skip pylint/flake8/eslint passes")
    ap.add_argument("--ai-key", default=os.environ.get("SMARTREPO_AI_KEY"),
                    help="OpenAI API key for smart summarization (or env SMARTREPO_AI_KEY)")
    ap.add_argument("--exclude", nargs="*", default=[],
                    help='Glob patterns to exclude, e.g. "*.min.js" "docs/*"')
    ap.add_argument("--include", nargs="*", default=[],
                    help="Glob patterns restricting which files are parsed")
    ap.add_argument("--workers", type=int, default=None,
                    help="Parallel workers for file analysis (default: CPU count)")

    sub.add_parser("gui", help="Launch the graphical interface")
    sub.add_parser("create-requirements", help="(Re)create requirements.txt")
    sub.add_parser("version", help="Print version")
    sub.add_parser("help", help="Show detailed help")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        app = SmartRepoAnalyzer()
        result = app.run(
            args.project_path,
            output_dir=args.output,
            enable_complexity=args.complexity,
            ai_api_key=args.ai_key,
            exclude=args.exclude,
            include=args.include,
            run_linters=not args.no_lint,
            quiet=args.quiet,
            verbose=args.verbose,
        )
        return 0 if result is not None else 1
    if args.command == "gui":
        launch_gui()
        return 0
    if args.command == "create-requirements":
        create_requirements_txt()
        return 0
    if args.command == "version":
        console.print(f"SmartRepo Analyzer v{__version__}")
        return 0
    # help / no command
    print_help()
    return 0


def print_help():
    console.print(Panel.fit(
        f"""[bold cyan]Welcome to SmartRepo Analyzer v{__version__}![/]
[dim]AI-Powered Code Analysis and Documentation Tool — أداة ذكية لتحليل الأكواد وتوليد التوثيق[/]

[bold]Commands[/]
  [green]analyze[/] <path>          Analyze a project and generate full reports
  [green]gui[/]                     Launch the desktop GUI
  [green]create-requirements[/]     Recreate requirements.txt
  [green]version[/]                 Show version information
  [green]help[/]                    This message

[bold]Analyze options[/]
  -o, --output DIR        Output directory (default: ./smartrepo-analysis)
  -v / -q                 Verbose diagnostics / quiet mode
  --complexity            Radon complexity + maintainability analysis
  --no-lint               Skip pylint/flake8/eslint
  --ai-key KEY            OpenAI summarization (env: SMARTREPO_AI_KEY)
  --exclude PAT...        Glob patterns to skip
  --include PAT...        Only analyze matching files
  --workers N             Parallel file workers

[bold]Examples[/]
  python smartrepo_analyzer.py analyze .
  python smartrepo_analyzer.py analyze ~/proj --complexity --exclude "*.min.js"
  python smartrepo_analyzer.py analyze . -o ./analysis --workers 4""",
        title="[bold yellow]SmartRepo[/]", border_style="blue",
    ))


if __name__ == "__main__":
    sys.exit(main())
