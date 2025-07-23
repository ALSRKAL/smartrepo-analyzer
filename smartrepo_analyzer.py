
#!/usr/bin/env python3
"""
SmartRepo Analyzer - AI-Powered Code Analysis and Documentation Tool
A comprehensive tool for analyzing codebases and generating AI-optimized documentation.
"""

import os
import json
import ast
import re
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib
from rich.progress import Progress, TimeElapsedColumn, TimeRemainingColumn
import time
from rich.progress import Progress

# Core dependencies (install with: pip install -r requirements.txt)
try:
    import yaml
    import toml
    from pygments.lexers import get_lexer_for_filename
    from pygments.util import ClassNotFound
except ImportError:
    print("Missing dependencies. Install with: pip install pyyaml toml pygments")
    exit(1)
# === دعم التغطية و linting ===
from coverage_support import parse_coverage_xml, get_overall_coverage
from linting_support import run_pylint_on_files
from monorepo_support import find_subprojects
from uml_support import generate_mermaid_class_diagram
from usage_example_support import extract_usage_examples
from summarization_support import summarize_file
from callgraph_support import extract_call_graph, save_call_graph_mermaid, find_cycles
from framework_detection_support import detect_frameworks
from git_support import get_contributors
from multi_lint_support import run_flake8_on_files, run_eslint_on_files
from recommendation_support import generate_recommendations
from complexity_support import analyze_complexity_with_radon, analyze_maintainability_with_radon
from security_support import analyze_security_with_bandit
from ai_summarization_support import ai_summarize_code

@dataclass
class FileInfo:
    """Information about a single file in the project"""
    path: str
    language: str
    size: int
    lines: int
    functions: List[str]
    classes: List[str]
    imports: List[str]
    complexity_score: int
    summary: str

@dataclass
class ProjectStructure:
    """Complete project analysis structure"""
    name: str
    type: str
    languages: List[str]
    entry_points: List[str]
    dependencies: Dict[str, List[str]]
    files: List[FileInfo]
    architecture: Dict[str, List[str]]
    metrics: Dict[str, Any]
    file_dependency_graph: Optional[Dict[str, List[str]]] = None  # NEW: العلاقات بين الملفات
    coverage: Optional[dict] = None  # NEW: نتائج التغطية
    overall_coverage: Optional[float] = None
    linting: Optional[list] = None   # NEW: نتائج linting
    call_graph_cycles: Optional[List[List[str]]] = None
    detected_frameworks: Optional[List[str]] = None
    contributors: Optional[List[Dict[str, Any]]] = None
    flake8: Optional[List[Dict[str, Any]]] = None
    eslint: Optional[List[Dict[str, Any]]] = None
    complexity: Optional[Dict[str, Any]] = None
    maintainability: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None
    ai_summaries: Optional[Dict[str, str]] = None

class CodeAnalyzer:
    """Core code analysis engine"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_structure = None
        self.supported_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React',
            '.tsx': 'React TypeScript',
            '.dart': 'Dart',
            '.rs': 'Rust',
            '.go': 'Go',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin'
        }

    def detect_project_type(self) -> Dict[str, Any]:
        """Auto-detect project type and main technologies"""
        project_info = {
            'type': 'Unknown',
            'framework': None,
            'languages': [],
            'package_managers': [],
            'entry_points': []
        }

        # Check for common config files
        config_files = {
            'package.json': self._analyze_package_json,
            'requirements.txt': self._analyze_requirements,
            'Pipfile': self._analyze_pipfile,
            'pubspec.yaml': self._analyze_pubspec,
            'Cargo.toml': self._analyze_cargo,
            'go.mod': self._analyze_go_mod,
            'pom.xml': self._analyze_maven,
            'composer.json': self._analyze_composer
        }

        for config_file, analyzer in config_files.items():
            config_path = self.project_path / config_file
            if config_path.exists():
                result = analyzer(config_path)
                project_info.update(result)
                break

        # Fallback: analyze file extensions
        if project_info['type'] == 'Unknown':
            project_info.update(self._analyze_by_extensions())

        return project_info

    def _analyze_package_json(self, path: Path) -> Dict[str, Any]:
        """Analyze Node.js package.json"""
        try:
            with open(path) as f:
                data = json.load(f)

            project_type = 'Node.js'
            framework = None
            languages = ['JavaScript']

            # Detect frameworks from dependencies
            deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}

            if any(key in deps for key in ['react', '@types/react']):
                framework = 'React'
                if '@types/react' in deps:
                    languages.append('TypeScript')
            elif 'vue' in deps:
                framework = 'Vue.js'
            elif 'angular' in deps or '@angular/core' in deps:
                framework = 'Angular'
                languages.append('TypeScript')
            elif 'express' in deps:
                framework = 'Express.js'
            elif 'next' in deps:
                framework = 'Next.js'

            # Check for TypeScript
            if 'typescript' in deps or any(f.suffix == '.ts' for f in self.project_path.rglob('*.ts')):
                languages.append('TypeScript')

            entry_points = []
            if 'main' in data:
                entry_points.append(data['main'])
            if 'scripts' in data and 'start' in data['scripts']:
                # Try to extract entry point from start script
                start_script = data['scripts']['start']
                if 'node' in start_script:
                    parts = start_script.split()
                    if len(parts) > 1:
                        entry_points.append(parts[-1])

            return {
                'type': project_type,
                'framework': framework,
                'languages': languages,
                'package_managers': ['npm'],
                'entry_points': entry_points
            }
        except Exception:
            return {'type': 'Node.js', 'languages': ['JavaScript']}

    def _analyze_requirements(self, path: Path) -> Dict[str, Any]:
        """Analyze Python requirements.txt"""
        frameworks = {
            'django': 'Django',
            'flask': 'Flask',
            'fastapi': 'FastAPI',
            'tornado': 'Tornado',
            'streamlit': 'Streamlit'
        }

        try:
            with open(path) as f:
                content = f.read().lower()

            detected_framework = None
            for pkg, framework in frameworks.items():
                if pkg in content:
                    detected_framework = framework
                    break

            return {
                'type': 'Python',
                'framework': detected_framework,
                'languages': ['Python'],
                'package_managers': ['pip'],
                'entry_points': self._find_python_entry_points()
            }
        except Exception:
            return {'type': 'Python', 'languages': ['Python']}

    def _analyze_pipfile(self, path: Path) -> Dict[str, Any]:
        """Analyze Python Pipfile"""
        return {
            'type': 'Python',
            'languages': ['Python'],
            'package_managers': ['pipenv'],
            'entry_points': self._find_python_entry_points()
        }

    def _analyze_pubspec(self, path: Path) -> Dict[str, Any]:
        """Analyze Flutter pubspec.yaml"""
        return {
            'type': 'Flutter',
            'framework': 'Flutter',
            'languages': ['Dart'],
            'package_managers': ['pub'],
            'entry_points': ['lib/main.dart']
        }

    def _analyze_cargo(self, path: Path) -> Dict[str, Any]:
        """Analyze Rust Cargo.toml"""
        return {
            'type': 'Rust',
            'languages': ['Rust'],
            'package_managers': ['cargo'],
            'entry_points': ['src/main.rs']
        }

    def _analyze_go_mod(self, path: Path) -> Dict[str, Any]:
        """Analyze Go go.mod"""
        return {
            'type': 'Go',
            'languages': ['Go'],
            'package_managers': ['go mod'],
            'entry_points': ['main.go']
        }

    def _analyze_maven(self, path: Path) -> Dict[str, Any]:
        """Analyze Java Maven pom.xml"""
        return {
            'type': 'Java',
            'framework': 'Maven',
            'languages': ['Java'],
            'package_managers': ['maven'],
            'entry_points': []
        }

    def _analyze_composer(self, path: Path) -> Dict[str, Any]:
        """Analyze PHP composer.json"""
        return {
            'type': 'PHP',
            'languages': ['PHP'],
            'package_managers': ['composer'],
            'entry_points': ['index.php']
        }

    def _analyze_by_extensions(self) -> Dict[str, Any]:
        """Fallback analysis by file extensions"""
        extension_count = defaultdict(int)

        for file_path in self.project_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in self.supported_extensions:
                extension_count[file_path.suffix] += 1

        if not extension_count:
            return {'type': 'Unknown', 'languages': []}

        # Find most common language
        primary_ext = max(extension_count.items(), key=lambda x: x[1])[0]
        primary_lang = self.supported_extensions[primary_ext]

        return {
            'type': primary_lang,
            'languages': [self.supported_extensions[ext] for ext in extension_count.keys()],
            'entry_points': []
        }

    def _find_python_entry_points(self) -> List[str]:
        """Find Python entry points"""
        entry_points = []
        common_names = ['main.py', 'app.py', 'run.py', 'server.py', 'manage.py']

        for name in common_names:
            if (self.project_path / name).exists():
                entry_points.append(name)

        return entry_points

    def analyze_file(self, file_path: Path) -> Optional[FileInfo]:
        """Analyze a single file"""
        try:
            if not file_path.is_file():
                return None

            # Get language
            try:
                lexer = get_lexer_for_filename(str(file_path))
                language = lexer.name
            except ClassNotFound:
                ext = file_path.suffix
                language = self.supported_extensions.get(ext, 'Unknown')

            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Skip binary files
                return None

            # Basic metrics
            lines = len(content.splitlines())
            size = len(content.encode('utf-8'))

            # Language-specific analysis
            functions = []
            classes = []
            imports = []
            complexity_score = 1

            if language == 'Python':
                result = self._analyze_python_file(content)
                functions = result['functions']
                classes = result['classes']
                imports = result['imports']
                complexity_score = result['complexity']
            elif language in ['JavaScript', 'TypeScript']:
                result = self._analyze_js_file(content)
                functions = result['functions']
                classes = result['classes']
                imports = result['imports']

            # Generate summary
            summary = self._generate_file_summary(file_path, language, functions, classes)

            return FileInfo(
                path=str(file_path.relative_to(self.project_path)),
                language=language,
                size=size,
                lines=lines,
                functions=functions,
                classes=classes,
                imports=imports,
                complexity_score=complexity_score,
                summary=summary
            )

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None

    def _analyze_python_file(self, content: str) -> Dict[str, Any]:
        """Analyze Python file using AST"""
        try:
            tree = ast.parse(content)

            functions = []
            classes = []
            imports = []
            complexity_score = 1

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                    # Simple complexity: count nested structures
                    complexity_score += sum(1 for _ in ast.walk(node) if isinstance(_, (ast.If, ast.For, ast.While)))
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    else:
                        imports.append(node.module or '')

            return {
                'functions': functions,
                'classes': classes,
                'imports': list(set(imports)),
                'complexity': complexity_score
            }
        except SyntaxError:
            return {'functions': [], 'classes': [], 'imports': [], 'complexity': 1}

    def _analyze_js_file(self, content: str) -> Dict[str, Any]:
        """Basic JavaScript/TypeScript analysis using regex"""
        # Simple regex-based analysis (for a production tool, use a proper parser)

        # Function patterns
        func_patterns = [
            r'function\s+(\w+)',
            r'const\s+(\w+)\s*=\s*(?:async\s+)?\(',
            r'let\s+(\w+)\s*=\s*(?:async\s+)?\(',
            r'var\s+(\w+)\s*=\s*(?:async\s+)?\(',
            r'(\w+):\s*(?:async\s+)?function',
            r'(\w+)\s*=\s*(?:async\s+)?\('
        ]

        functions = []
        for pattern in func_patterns:
            functions.extend(re.findall(pattern, content))

        # Class patterns
        classes = re.findall(r'class\s+(\w+)', content)

        # Import patterns
        import_patterns = [
            r'import.*from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]',
            r'require\([\'"]([^\'"]+)[\'"]\)'
        ]

        imports = []
        for pattern in import_patterns:
            imports.extend(re.findall(pattern, content))

        return {
            'functions': list(set(functions)),
            'classes': list(set(classes)),
            'imports': list(set(imports))
        }

    def _generate_file_summary(self, file_path: Path, language: str, functions: List[str], classes: List[str]) -> str:
        """Generate AI-friendly file summary"""
        parts = []
        parts.append(f"{language} file")

        if classes:
            parts.append(f"defines {len(classes)} class(es): {', '.join(classes[:3])}")

        if functions:
            parts.append(f"contains {len(functions)} function(s): {', '.join(functions[:3])}")

        # Infer purpose from filename and structure
        name = file_path.name.lower()
        if 'test' in name:
            parts.append("(testing module)")
        elif 'util' in name or 'helper' in name:
            parts.append("(utility module)")
        elif 'config' in name:
            parts.append("(configuration)")
        elif 'model' in name:
            parts.append("(data model)")
        elif 'controller' in name or 'route' in name:
            parts.append("(request handler)")
        elif 'service' in name:
            parts.append("(business logic)")

        return ' '.join(parts)

    def analyze_project(self, ai_api_key: str = None, enable_complexity: bool = False) -> ProjectStructure:
        """Perform complete project analysis"""
        print("🔍 Starting project analysis...")

        # Detect project type
        project_info = self.detect_project_type()
        print(f"✓ Project type: {project_info['type']}")
        if project_info['framework']:
            print(f"✓ Framework: {project_info['framework']}")

        # Analyze all files with progress bar
        files = []
        file_count = 0
        all_files = [f for f in self.project_path.rglob('*') if self._should_analyze_file(f)]
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing files...", total=len(all_files))
            for file_path in all_files:
                file_info = self.analyze_file(file_path)
                if file_info:
                    files.append(file_info)
                    file_count += 1
                progress.update(task, advance=1, description=f"[cyan]Analyzing: {file_path.name}")
        print(f"✓ Analyzed {file_count} files")

        # Extract dependencies
        dependencies = self._extract_dependencies()
        # Categorize architecture
        architecture = self._categorize_architecture(files)
        # Calculate metrics
        metrics = self._calculate_metrics(files)
        # NEW: Build dependency graph
        file_dependency_graph = self._build_file_dependency_graph(files)
        # === تحليل التغطية ===
        coverage_xml = self.project_path / 'coverage.xml'
        coverage_data = parse_coverage_xml(coverage_xml)
        overall_coverage = get_overall_coverage(coverage_data) if coverage_data else None
        # === تحليل linting ===
        py_files = [self.project_path / f.path for f in files if f.language == 'Python']
        linting_results = run_pylint_on_files(py_files) if py_files else None
        # === تحليل call graph ===
        call_graph = extract_call_graph(py_files)
        save_call_graph_mermaid(call_graph, self.project_path / 'call-graph.mmd')
        cycles = find_cycles(call_graph)
        # === اكتشاف الأطر ===
        all_files = [self.project_path / f.path for f in files]
        detected_frameworks = detect_frameworks(all_files)
        # === إحصائيات git ===
        contributors = get_contributors(self.project_path)
        # === linting متعدد ===
        flake8_results = run_flake8_on_files(py_files)
        js_files = [self.project_path / f.path for f in files if f.language in ['JavaScript', 'TypeScript']]
        eslint_results = run_eslint_on_files(js_files)
        # === تحليل التعقيد (radon) ===
        if enable_complexity and py_files:
            print("[yellow]Starting complexity analysis (radon)...[/yellow]")
            with Progress("[progress.description]{task.description}",
                          TimeElapsedColumn(),
                          TimeRemainingColumn(),
                          "{task.completed}/{task.total}") as progress:
                task = progress.add_task("[magenta]Complexity analysis...", total=len(py_files))
                complexity_results = {}
                start = time.time()
                for pyf in py_files:
                    from complexity_support import analyze_complexity_with_radon
                    res = analyze_complexity_with_radon([pyf])
                    complexity_results.update(res)
                    progress.update(task, advance=1, description=f"[magenta]Analyzing: {pyf.name}")
                elapsed = time.time() - start
                print(f"[green]✓ Complexity analysis done in {elapsed:.1f} seconds[/green]")
            from complexity_support import analyze_maintainability_with_radon
            maintainability_results = analyze_maintainability_with_radon(py_files)
        else:
            complexity_results = None
            maintainability_results = None
        # === تحليل الأمان (bandit) ===
        security_results = analyze_security_with_bandit(py_files)
        # === تلخيص ذكي (اختياري) ===
        ai_summaries = {}
        if ai_api_key:
            for file in py_files:
                ai_summaries[str(file)] = ai_summarize_code(file, ai_api_key)
        self.project_structure = ProjectStructure(
            name=self.project_path.name,
            type=project_info['type'],
            languages=project_info['languages'],
            entry_points=project_info['entry_points'],
            dependencies=dependencies,
            files=files,
            architecture=architecture,
            metrics=metrics,
            file_dependency_graph=file_dependency_graph,
            coverage=coverage_data,
            overall_coverage=overall_coverage,
            linting=linting_results,
            call_graph_cycles=cycles,
            detected_frameworks=list(detected_frameworks),
            contributors=contributors,
            flake8=flake8_results,
            eslint=eslint_results,
            complexity=complexity_results,
            maintainability=maintainability_results,
            security=security_results,
            ai_summaries=ai_summaries
        )
        return self.project_structure

    def _should_analyze_file(self, file_path: Path) -> bool:
        """Determine if file should be analyzed"""
        # Skip hidden files and directories
        if any(part.startswith('.') for part in file_path.parts):
            return False

        # Skip common ignore patterns
        ignore_patterns = [
            'node_modules', '__pycache__', '.git', 'venv', 'env',
            'dist', 'build', 'target', '.pytest_cache'
        ]

        if any(pattern in str(file_path) for pattern in ignore_patterns):
            return False

        # Only analyze supported file types
        return file_path.suffix in self.supported_extensions

    def _extract_dependencies(self) -> Dict[str, List[str]]:
        """Extract project dependencies from config files"""
        deps = {'runtime': [], 'development': []}

        # Package.json
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                deps['runtime'].extend(data.get('dependencies', {}).keys())
                deps['development'].extend(data.get('devDependencies', {}).keys())
            except Exception:
                pass

        # Requirements.txt
        requirements = self.project_path / 'requirements.txt'
        if requirements.exists():
            try:
                with open(requirements) as f:
                    deps['runtime'].extend([
                        line.split('==')[0].split('>=')[0].strip()
                        for line in f if line.strip() and not line.startswith('#')
                    ])
            except Exception:
                pass

        return deps

    def _categorize_architecture(self, files: List[FileInfo]) -> Dict[str, List[str]]:
        """Categorize files by architectural role"""
        categories = {
            'Models': [],
            'Controllers': [],
            'Views': [],
            'Services': [],
            'Utils': [],
            'Tests': [],
            'Config': [],
            'Other': []
        }

        for file_info in files:
            path_lower = file_info.path.lower()

            if 'test' in path_lower:
                categories['Tests'].append(file_info.path)
            elif any(term in path_lower for term in ['model', 'schema', 'entity']):
                categories['Models'].append(file_info.path)
            elif any(term in path_lower for term in ['controller', 'route', 'handler']):
                categories['Controllers'].append(file_info.path)
            elif any(term in path_lower for term in ['view', 'component', 'template']):
                categories['Views'].append(file_info.path)
            elif any(term in path_lower for term in ['service', 'business', 'logic']):
                categories['Services'].append(file_info.path)
            elif any(term in path_lower for term in ['util', 'helper', 'tool']):
                categories['Utils'].append(file_info.path)
            elif any(term in path_lower for term in ['config', 'setting', 'env']):
                categories['Config'].append(file_info.path)
            else:
                categories['Other'].append(file_info.path)

        return categories

    def _calculate_metrics(self, files: List[FileInfo]) -> Dict[str, Any]:
        """Calculate project metrics"""
        total_lines = sum(f.lines for f in files)
        total_files = len(files)
        total_functions = sum(len(f.functions) for f in files)
        total_classes = sum(len(f.classes) for f in files)
        avg_complexity = sum(f.complexity_score for f in files) / total_files if total_files > 0 else 0

        language_distribution = defaultdict(int)
        for file_info in files:
            language_distribution[file_info.language] += file_info.lines

        return {
            'total_files': total_files,
            'total_lines': total_lines,
            'total_functions': total_functions,
            'total_classes': total_classes,
            'average_complexity': round(avg_complexity, 2),
            'language_distribution': dict(language_distribution)
        }

    def _build_file_dependency_graph(self, files: List[FileInfo]) -> Dict[str, List[str]]:
        """بناء رسم علاقات الاستيراد بين الملفات (dependency graph)"""
        # فقط للملفات التي تم تحليلها
        file_map = {f.path: f for f in files}
        dep_graph = {f.path: [] for f in files}
        # ابحث عن كل import يشير إلى ملف آخر في المشروع
        for file in files:
            for imp in file.imports:
                # ابحث عن ملف يحمل نفس اسم import (بدون الامتداد)
                for other in files:
                    if other is file:
                        continue
                    # Python: import mymodule -> mymodule.py
                    if imp == Path(other.path).stem or imp == other.path.replace("/", ".").rsplit(".", 1)[0]:
                        dep_graph[file.path].append(other.path)
        return dep_graph

class DocumentationGenerator:
    """Generates enhanced documentation and visualizations"""

    def __init__(self, project_structure: ProjectStructure, output_dir: Path):
        self.structure = project_structure
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def generate_all(self):
        """Generate all documentation outputs"""
        print("📝 Generating documentation...")

        self.generate_enhanced_readme()
        self.generate_architecture_diagram()
        self.generate_file_dependency_diagram()
        self.generate_ai_summary()
        self.generate_prompt_ready()
        self.generate_uml_diagram()
        self.generate_usage_examples_file()
        self.generate_file_summaries()
        print(self._generate_code_quality_section())
        print("✅ Documentation generation complete!")
        print(f"📁 Output files saved to: {self.output_dir}")

        # إضافة call-graph.mmd
        if hasattr(self.structure, 'call_graph_cycles') and self.structure.call_graph_cycles:
            with open(self.output_dir / 'call-graph-cycles.txt', 'w', encoding='utf-8') as f:
                for cycle in self.structure.call_graph_cycles:
                    f.write(' -> '.join(cycle) + '\n')
        # إضافة contributors
        if hasattr(self.structure, 'contributors'):
            with open(self.output_dir / 'contributors.txt', 'w', encoding='utf-8') as f:
                for c in self.structure.contributors:
                    f.write(f"{c['name']}: {c['commits']} commits\n")
        # إضافة linting متعدد
        if hasattr(self.structure, 'flake8'):
            with open(self.output_dir / 'flake8-linting.json', 'w', encoding='utf-8') as f:
                import json; f.write(json.dumps(self.structure.flake8, ensure_ascii=False, indent=2))
        if hasattr(self.structure, 'eslint'):
            with open(self.output_dir / 'eslint-linting.json', 'w', encoding='utf-8') as f:
                import json; f.write(json.dumps(self.structure.eslint, ensure_ascii=False, indent=2))
        # إضافة توصيات ذكية
        from recommendation_support import generate_recommendations
        recs = generate_recommendations(self.structure.metrics, self.structure.overall_coverage, len(self.structure.linting) if self.structure.linting else 0)
        with open(self.output_dir / 'recommendations.txt', 'w', encoding='utf-8') as f:
            for r in recs:
                f.write(r + '\n')
        # إضافة تقارير التعقيد والأمان والتلخيص الذكي
        if hasattr(self.structure, 'complexity'):
            with open(self.output_dir / 'complexity_report.json', 'w', encoding='utf-8') as f:
                import json; f.write(json.dumps(self.structure.complexity, ensure_ascii=False, indent=2))
        if hasattr(self.structure, 'maintainability'):
            with open(self.output_dir / 'maintainability_report.json', 'w', encoding='utf-8') as f:
                import json; f.write(json.dumps(self.structure.maintainability, ensure_ascii=False, indent=2))
        if hasattr(self.structure, 'security'):
            with open(self.output_dir / 'security_report.json', 'w', encoding='utf-8') as f:
                import json; f.write(json.dumps(self.structure.security, ensure_ascii=False, indent=2))
        if hasattr(self.structure, 'ai_summaries') and self.structure.ai_summaries:
            with open(self.output_dir / 'ai_summaries.txt', 'w', encoding='utf-8') as f:
                for file, summary in self.structure.ai_summaries.items():
                    f.write(f"# {file}\n{summary}\n\n")

    def generate_enhanced_readme(self):
        """Generate enhanced README.md"""
        coverage_str = f"{self.structure.overall_coverage:.1f}%" if self.structure.overall_coverage is not None else "Not available"
        linting_str = str(len(self.structure.linting)) if self.structure.linting else "0"
        readme_content = f"""# {self.structure.name}

## 🚀 Overview
{self._generate_project_description()}

## 📊 Project Statistics
- **Type**: {self.structure.type}
- **Languages**: {', '.join(self.structure.languages)}
- **Total Files**: {self.structure.metrics['total_files']}
- **Total Lines**: {self.structure.metrics['total_lines']:,}
- **Functions**: {self.structure.metrics['total_functions']}
- **Classes**: {self.structure.metrics['total_classes']}
- **Coverage**: {coverage_str}\n- **Linting Issues**: {linting_str}\n
## 🏗️ Architecture

```
{self._generate_architecture_tree()}
```

### 📂 Project Structure
{self._generate_structure_description()}

## 🔧 Dependencies
{self._generate_dependencies_section()}

## 🚀 Getting Started

### Prerequisites
{self._generate_prerequisites()}

### Installation
{self._generate_installation_steps()}

### Usage
{self._generate_usage_examples()}

## 📈 Code Metrics
- **Average Complexity**: {self.structure.metrics['average_complexity']}
- **Language Distribution**:
{self._format_language_distribution()}

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*This README was auto-generated by SmartRepo*
"""

        with open(self.output_dir / 'readme-enhanced.md', 'w') as f:
            f.write(readme_content)

    def _generate_project_description(self) -> str:
        """Generate intelligent project description"""
        desc_parts = []

        if self.structure.type == 'Node.js':
            desc_parts.append("A Node.js application")
        elif self.structure.type == 'Python':
            desc_parts.append("A Python application")
        elif self.structure.type == 'Flutter':
            desc_parts.append("A Flutter mobile application")
        else:
            desc_parts.append(f"A {self.structure.type} application")

        # Add framework info
        main_files = [f for f in self.structure.files if any(ep in f.path for ep in self.structure.entry_points)]
        if main_files:
            desc_parts.append(f"with main entry point at `{main_files[0].path}`")

        # Add architecture insights
        if self.structure.architecture['Models']:
            desc_parts.append("featuring a well-structured data layer")

        if self.structure.architecture['Services']:
            desc_parts.append("with dedicated business logic services")

        return '. '.join(desc_parts) + '.'

    def _generate_architecture_tree(self) -> str:
        """Generate ASCII tree of project structure"""
        tree_lines = []

        for category, files in self.structure.architecture.items():
            if files:
                tree_lines.append(f"├── {category}/")
                for i, file_path in enumerate(files):  # عرض كل الملفات
                    prefix = "│   ├──" if i < len(files) - 1 else "│   └──"
                    tree_lines.append(f"{prefix} {Path(file_path).name}")

        return '\n'.join(tree_lines)

    def _generate_structure_description(self) -> str:
        """Generate structure description"""
        descriptions = []

        for category, files in self.structure.architecture.items():
            if files:
                count = len(files)
                if category == 'Models':
                    descriptions.append(f"- **{category}** ({count} files): Data models and schemas")
                elif category == 'Controllers':
                    descriptions.append(f"- **{category}** ({count} files): Request handlers and route controllers")
                elif category == 'Views':
                    descriptions.append(f"- **{category}** ({count} files): UI components and templates")
                elif category == 'Services':
                    descriptions.append(f"- **{category}** ({count} files): Business logic and services")
                elif category == 'Utils':
                    descriptions.append(f"- **{category}** ({count} files): Utility functions and helpers")
                elif category == 'Tests':
                    descriptions.append(f"- **{category}** ({count} files): Test suites and specifications")
                elif category == 'Config':
                    descriptions.append(f"- **{category}** ({count} files): Configuration files")
                else:
                    descriptions.append(f"- **{category}** ({count} files): Other project files")

        return '\n'.join(descriptions)

    def _generate_dependencies_section(self) -> str:
        """Generate dependencies section"""
        sections = []

        if self.structure.dependencies['runtime']:
            sections.append("### Runtime Dependencies")
            runtime_deps = self.structure.dependencies['runtime'][:10]  # Show first 10
            for dep in runtime_deps:
                sections.append(f"- `{dep}`")
            if len(self.structure.dependencies['runtime']) > 10:
                sections.append(f"- ... and {len(self.structure.dependencies['runtime']) - 10} more")

        if self.structure.dependencies['development']:
            sections.append("\n### Development Dependencies")
            dev_deps = self.structure.dependencies['development'][:10]
            for dep in dev_deps:
                sections.append(f"- `{dep}`")
            if len(self.structure.dependencies['development']) > 10:
                sections.append(f"- ... and {len(self.structure.dependencies['development']) - 10} more")

        return '\n'.join(sections) if sections else "No dependencies detected."

    def _generate_prerequisites(self) -> str:
        """Generate prerequisites section"""
        prereqs = []

        if self.structure.type == 'Node.js':
            prereqs.append("- Node.js (v14 or higher)")
            prereqs.append("- npm or yarn")
        elif self.structure.type == 'Python':
            prereqs.append("- Python 3.7+")
            prereqs.append("- pip")
        elif self.structure.type == 'Flutter':
            prereqs.append("- Flutter SDK")
            prereqs.append("- Dart SDK")
        elif self.structure.type == 'Rust':
            prereqs.append("- Rust toolchain")
            prereqs.append("- Cargo")
        elif self.structure.type == 'Go':
            prereqs.append("- Go 1.16+")

        return '\n'.join(prereqs) if prereqs else "- Check project documentation for specific requirements"

    def _generate_installation_steps(self) -> str:
        """Generate installation steps"""
        steps = ["```bash", "# Clone the repository", f"git clone <repository-url>", f"cd {self.structure.name}", ""]

        if self.structure.type == 'Node.js':
            steps.extend(["# Install dependencies", "npm install", ""])
        elif self.structure.type == 'Python':
            steps.extend(["# Install dependencies", "pip install -r requirements.txt", ""])
        elif self.structure.type == 'Flutter':
            steps.extend(["# Get dependencies", "flutter pub get", ""])
        elif self.structure.type == 'Rust':
            steps.extend(["# Build the project", "cargo build", ""])
        elif self.structure.type == 'Go':
            steps.extend(["# Download dependencies", "go mod download", ""])

        steps.append("```")
        return '\n'.join(steps)

    def _generate_usage_examples(self) -> str:
        """Generate usage examples"""
        examples = ["```bash"]

        if self.structure.entry_points:
            entry_point = self.structure.entry_points[0]

            if self.structure.type == 'Node.js':
                examples.append(f"# Start the application")
                examples.append(f"npm start")
                examples.append(f"# or")
                examples.append(f"node {entry_point}")
            elif self.structure.type == 'Python':
                examples.append(f"# Run the application")
                examples.append(f"python {entry_point}")
            elif self.structure.type == 'Flutter':
                examples.append(f"# Run the app")
                examples.append(f"flutter run")
            elif self.structure.type == 'Rust':
                examples.append(f"# Run the application")
                examples.append(f"cargo run")
            elif self.structure.type == 'Go':
                examples.append(f"# Run the application")
                examples.append(f"go run {entry_point}")
        else:
            examples.append("# Check project documentation for usage instructions")

        examples.append("```")
        return '\n'.join(examples)

    def _format_language_distribution(self) -> str:
        """Format language distribution"""
        total_lines = sum(self.structure.metrics['language_distribution'].values())
        lines = []

        for lang, line_count in sorted(self.structure.metrics['language_distribution'].items(),
                                     key=lambda x: x[1], reverse=True):
            percentage = (line_count / total_lines * 100) if total_lines > 0 else 0
            lines.append(f"  - **{lang}**: {line_count:,} lines ({percentage:.1f}%)")

        return '\n'.join(lines)

    def generate_architecture_diagram(self):
        """Generate Mermaid architecture diagram"""
        mermaid_content = self._generate_mermaid_diagram()

        with open(self.output_dir / 'architecture.mmd', 'w') as f:
            f.write(mermaid_content)

        # Try to generate PNG if mermaid-cli is available
        self._generate_diagram_png()

    def _generate_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram content"""
        diagram_lines = ["graph TD"]

        # Add main application node
        diagram_lines.append(f"    APP[{self.structure.name}]")

        # Add category nodes and connections
        node_id = 0
        category_nodes = {}

        for category, files in self.structure.architecture.items():
            if files:
                node_id += 1
                category_node = f"CAT{node_id}"
                category_nodes[category] = category_node

                # Style based on category
                if category == 'Controllers':
                    diagram_lines.append(f"    {category_node}[{category}]:::controller")
                elif category == 'Models':
                    diagram_lines.append(f"    {category_node}[{category}]:::model")
                elif category == 'Views':
                    diagram_lines.append(f"    {category_node}[{category}]:::view")
                elif category == 'Services':
                    diagram_lines.append(f"    {category_node}[{category}]:::service")
                else:
                    diagram_lines.append(f"    {category_node}[{category}]")

                diagram_lines.append(f"    APP --> {category_node}")

                # Add كل الملفات
                for i, file_path in enumerate(files):
                    node_id += 1
                    file_node = f"FILE{node_id}"
                    file_name = Path(file_path).name
                    diagram_lines.append(f"    {file_node}[{file_name}]")
                    diagram_lines.append(f"    {category_node} --> {file_node}")

        # Add styling
        diagram_lines.extend([
            "",
            "    classDef controller fill:#e1f5fe",
            "    classDef model fill:#f3e5f5",
            "    classDef view fill:#e8f5e8",
            "    classDef service fill:#fff3e0"
        ])

        return '\n'.join(diagram_lines)

    def _generate_diagram_png(self):
        """Try to generate PNG from Mermaid (requires mermaid-cli)"""
        try:
            input_file = self.output_dir / 'architecture.mmd'
            output_file = self.output_dir / 'architecture.png'

            result = subprocess.run([
                'mmdc', '-i', str(input_file), '-o', str(output_file),
                '-t', 'neutral', '-b', 'white'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("✓ Architecture PNG generated")
            else:
                print("⚠ Mermaid CLI not available. Install with: npm install -g @mermaid-js/mermaid-cli")
        except FileNotFoundError:
            print("⚠ Mermaid CLI not found. PNG generation skipped.")

    def generate_file_dependency_diagram(self):
        """توليد مخطط Mermaid يوضح العلاقات بين الملفات (dependency graph)"""
        dep_graph = self.structure.file_dependency_graph
        if not dep_graph:
            print("لا يوجد رسم علاقات بين الملفات")
            return
        lines = ["graph TD"]
        for src, targets in dep_graph.items():
            src_node = src.replace("/", "_").replace(".", "_")
            if not targets:
                lines.append(f"    {src_node}['{src}']")
            for tgt in targets:
                tgt_node = tgt.replace("/", "_").replace(".", "_")
                lines.append(f"    {src_node}['{src}'] --> {tgt_node}['{tgt}']")
        with open(self.output_dir / 'file-dependency-graph.mmd', 'w') as f:
            f.write('\n'.join(lines))
        print("✓ تم توليد مخطط علاقات الملفات: file-dependency-graph.mmd")

    def generate_ai_summary(self):
        """Generate AI-friendly JSON summary"""
        summary = {
            "project_overview": {
                "name": self.structure.name,
                "type": self.structure.type,
                "languages": self.structure.languages,
                "entry_points": self.structure.entry_points,
                "description": self._generate_project_description()
            },
            "metrics": self.structure.metrics,
            "dependencies": self.structure.dependencies,
            "architecture": {
                category: {
                    "file_count": len(files),
                    "files": files,  # كل الملفات
                    "description": self._get_category_description(category)
                }
                for category, files in self.structure.architecture.items()
                if files
            },
            "file_summaries": [
                {
                    "path": file.path,
                    "language": file.language,
                    "summary": file.summary,
                    "functions": file.functions[:10],  # First 10 functions
                    "classes": file.classes,
                    "lines": file.lines,
                    "complexity": file.complexity_score
                }
                for file in sorted(self.structure.files, key=lambda x: x.lines, reverse=True)[:20]  # Top 20 files
            ],
            "key_insights": self._generate_key_insights(),
            "generated_at": "2025-07-23T00:00:00Z",
            "analyzer_version": "1.0.0"
        }

        with open(self.output_dir / 'ai-summary.json', 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def _get_category_description(self, category: str) -> str:
        """Get description for architecture category"""
        descriptions = {
            'Models': 'Data models, schemas, and database entities',
            'Controllers': 'Request handlers, route controllers, and API endpoints',
            'Views': 'UI components, templates, and presentation layer',
            'Services': 'Business logic, services, and core functionality',
            'Utils': 'Utility functions, helpers, and common tools',
            'Tests': 'Test suites, unit tests, and testing utilities',
            'Config': 'Configuration files and environment settings',
            'Other': 'Miscellaneous files and additional components'
        }
        return descriptions.get(category, 'Project files')

    def _generate_key_insights(self) -> List[str]:
        """Generate key insights about the project"""
        insights = []

        # Complexity insights
        if self.structure.metrics['average_complexity'] > 5:
            insights.append("High code complexity detected - consider refactoring for maintainability")
        elif self.structure.metrics['average_complexity'] < 2:
            insights.append("Low complexity code - well-structured and maintainable")

        # Architecture insights
        if self.structure.architecture['Tests']:
            test_ratio = len(self.structure.architecture['Tests']) / self.structure.metrics['total_files']
            if test_ratio > 0.3:
                insights.append("Good test coverage - testing is well-integrated")
            elif test_ratio < 0.1:
                insights.append("Limited test files detected - consider improving test coverage")

        if self.structure.architecture['Models'] and self.structure.architecture['Controllers']:
            insights.append("Follows MVC-like architecture pattern")

        if self.structure.architecture['Services']:
            insights.append("Service-oriented architecture detected")

        # Language insights
        lang_count = len(self.structure.metrics['language_distribution'])
        if lang_count > 3:
            insights.append(f"Multi-language project ({lang_count} languages) - good for diverse functionality")

        # Size insights
        if self.structure.metrics['total_lines'] > 10000:
            insights.append("Large codebase - consider modularization strategies")
        elif self.structure.metrics['total_lines'] < 1000:
            insights.append("Compact project - good for quick understanding and maintenance")

        return insights

    def generate_prompt_ready(self):
        """Generate prompt-ready documentation for AI consumption"""
        content = f"""# AI-Ready Project Analysis: {self.structure.name}

## Quick Summary
This is a {self.structure.type} project with {self.structure.metrics['total_files']} files and {self.structure.metrics['total_lines']:,} lines of code across {len(self.structure.languages)} programming languages.

## Project Context
**Type**: {self.structure.type}
**Languages**: {', '.join(self.structure.languages)}
**Entry Points**: {', '.join(self.structure.entry_points) if self.structure.entry_points else 'Not specified'}

## Architecture Overview
{self._generate_architecture_prompt_section()}

## Key Components
{self._generate_components_prompt_section()}

## Code Characteristics
- **Complexity Level**: {'High' if self.structure.metrics['average_complexity'] > 5 else 'Medium' if self.structure.metrics['average_complexity'] > 3 else 'Low'}
- **Total Functions**: {self.structure.metrics['total_functions']}
- **Total Classes**: {self.structure.metrics['total_classes']}
- **Testing**: {'Well-tested' if self.structure.architecture['Tests'] else 'Limited testing'}

## Dependencies Context
{self._generate_dependencies_prompt_section()}

## File Structure Summary
{self._generate_file_structure_prompt()}

## Development Insights
{chr(10).join(f'- {insight}' for insight in self._generate_key_insights())}

## Language Distribution
{self._generate_language_prompt_section()}

---
*This analysis provides AI-ready context for understanding, documenting, or extending this codebase.*
"""

        with open(self.output_dir / 'prompt-ready.md', 'w') as f:
            f.write(content)

    def _generate_architecture_prompt_section(self) -> str:
        """Generate architecture section for prompts"""
        sections = []

        for category, files in self.structure.architecture.items():
            if files:
                count = len(files)
                sections.append(f"**{category}** ({count} files): {self._get_category_description(category)}")

        return '\n'.join(sections)

    def _generate_components_prompt_section(self) -> str:
        """Generate components section for prompts"""
        components = []

        # Get top files by different criteria
        largest_files = sorted(self.structure.files, key=lambda x: x.lines, reverse=True)[:5]
        most_complex = sorted(self.structure.files, key=lambda x: x.complexity_score, reverse=True)[:3]

        components.append("**Largest Files**:")
        for file in largest_files:
            components.append(f"- `{file.path}` ({file.lines} lines, {file.language}): {file.summary}")

        if most_complex[0].complexity_score > 3:
            components.append("\n**Most Complex Files**:")
            for file in most_complex:
                if file.complexity_score > 3:
                    components.append(f"- `{file.path}` (complexity: {file.complexity_score}): {file.summary}")

        return '\n'.join(components)

    def _generate_dependencies_prompt_section(self) -> str:
        """Generate dependencies section for prompts"""
        sections = []

        if self.structure.dependencies['runtime']:
            key_deps = self.structure.dependencies['runtime'][:8]
            sections.append(f"**Key Runtime Dependencies**: {', '.join(key_deps)}")

        if self.structure.dependencies['development']:
            dev_deps = self.structure.dependencies['development'][:5]
            sections.append(f"**Development Tools**: {', '.join(dev_deps)}")

        return '\n'.join(sections) if sections else "No major dependencies detected."

    def _generate_file_structure_prompt(self) -> str:
        """Generate file structure for prompts"""
        structure = []

        for category, files in self.structure.architecture.items():
            if files:
                structure.append(f"- **{category}**: {len(files)} files")
                # Show a few example files
                examples = [Path(f).name for f in files[:3]]
                structure.append(f"  Examples: {', '.join(examples)}")

        return '\n'.join(structure)

    def _generate_language_prompt_section(self) -> str:
        """Generate language distribution for prompts"""
        total_lines = sum(self.structure.metrics['language_distribution'].values())
        sections = []

        for lang, lines in sorted(self.structure.metrics['language_distribution'].items(),
                                key=lambda x: x[1], reverse=True):
            percentage = (lines / total_lines * 100) if total_lines > 0 else 0
            sections.append(f"- **{lang}**: {percentage:.1f}% ({lines:,} lines)")

        return '\n'.join(sections)

    def _generate_code_quality_section(self) -> str:
        """إضافة ملخص التغطية و linting في قسم منفصل"""
        lines = []
        if self.structure.overall_coverage is not None:
            lines.append(f"- **Test Coverage**: {self.structure.overall_coverage:.1f}%")
        if self.structure.linting:
            issues = [l for l in self.structure.linting if l.get('type') == 'convention' or l.get('type') == 'error']
            lines.append(f"- **Linting Issues**: {len(issues)} (convention/error)")
        return '\n'.join(lines) if lines else "- No code quality data."

    def generate_uml_diagram(self):
        """توليد مخطط UML class diagram وحفظه"""
        py_files = [self.output_dir.parent / f.path for f in self.structure.files if f.language == 'Python']
        if py_files:
            output_path = self.output_dir / 'uml-class-diagram.mmd'
            generate_mermaid_class_diagram(py_files, output_path)
            print("✓ تم توليد مخطط UML class diagram")
    def generate_usage_examples_file(self):
        """توليد ملف أمثلة استخدام تلقائية"""
        py_files = [self.output_dir.parent / f.path for f in self.structure.files if f.language == 'Python']
        if py_files:
            examples = extract_usage_examples(py_files)
            with open(self.output_dir / 'usage-examples.txt', 'w', encoding='utf-8') as f:
                for ex in examples:
                    f.write(ex + '\n')
            print(f"✓ تم توليد أمثلة استخدام: {len(examples)} مثال")
    def generate_file_summaries(self):
        """تلخيص الملفات الكبيرة وحفظها"""
        # استخدم المسار الأصلي للمشروع
        project_root = self.output_dir.parent  # مجلد المشروع الأصلي
        for f in self.structure.files:
            if f.lines > 100:
                src_path = project_root / f.path
                if src_path.exists():
                    summary = summarize_file(src_path)
                    with open(self.output_dir / f"summary_{Path(f.path).name}.txt", 'w', encoding='utf-8') as out:
                        out.write(summary)
        print("✓ تم تلخيص الملفات الكبيرة")


class SmartRepoAnalyzer:
    """Main application class"""

    def __init__(self):
        self.version = "1.0.0"

    def run(self, project_path: str, output_dir: Optional[str] = None, enable_complexity: bool = False):
        """Run the complete analysis pipeline"""
        print(f"🚀 SmartRepo Analyzer v{self.version}")
        print(f"📁 Analyzing project: {project_path}")
        project_path = Path(project_path).resolve()
        if not project_path.exists():
            print(f"❌ Error: Project path '{project_path}' does not exist")
            return
        output_path = Path(output_dir) if output_dir else project_path / 'smartrepo-analysis'
        try:
            # دعم monorepo: تحليل كل مشروع فرعي
            subprojects = find_subprojects(project_path)
            if subprojects:
                print(f"🔎 Found {len(subprojects)} subprojects (monorepo mode)")
                for sub in subprojects:
                    print(f"\n=== Analyzing subproject: {sub} ===")
                    sub_output = output_path / sub.name
                    sub_output.mkdir(parents=True, exist_ok=True)
                    analyzer = CodeAnalyzer(str(sub))
                    project_structure = analyzer.analyze_project(enable_complexity=enable_complexity)
                    doc_generator = DocumentationGenerator(project_structure, sub_output)
                    doc_generator.generate_all()
                    self._print_summary(project_structure, sub_output)
                print(f"\n🎉 All subproject analyses saved to: {output_path}")
                return
            # Initialize analyzer
            analyzer = CodeAnalyzer(str(project_path))
            # Perform analysis
            project_structure = analyzer.analyze_project(enable_complexity=enable_complexity)
            # Generate documentation
            doc_generator = DocumentationGenerator(project_structure, output_path)
            doc_generator.generate_all()
            # Print summary
            self._print_summary(project_structure, output_path)
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()

    def _print_summary(self, structure: ProjectStructure, output_path: Path):
        """Print analysis summary"""
        print("\n" + "="*60)
        print("📊 ANALYSIS COMPLETE")
        print("="*60)
        print(f"Project: {structure.name}")
        print(f"Type: {structure.type}")
        print(f"Languages: {', '.join(structure.languages)}")
        print(f"Files analyzed: {structure.metrics['total_files']}")
        print(f"Total lines: {structure.metrics['total_lines']:,}")
        print(f"Functions: {structure.metrics['total_functions']}")
        print(f"Classes: {structure.metrics['total_classes']}")
        print(f"Average complexity: {structure.metrics['average_complexity']}")
        print("\n📁 Generated files:")

        output_files = [
            'readme-enhanced.md',
            'architecture.mmd',
            'ai-summary.json',
            'prompt-ready.md'
        ]

        for filename in output_files:
            file_path = output_path / filename
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  ✓ {filename} ({size:,} bytes)")
            else:
                print(f"  ⚠ {filename} (not generated)")

        print(f"\n🎉 All files saved to: {output_path}")


def create_requirements_txt():
    """Create requirements.txt file"""
    requirements = """# SmartRepo Analyzer Requirements
pyyaml>=6.0
toml>=0.10.2
pygments>=2.10.0
requests>=2.25.0
click>=8.0.0
pathlib2>=2.3.6
dataclasses>=0.6; python_version<"3.7"
"""

    with open('requirements.txt', 'w') as f:
        f.write(requirements)
    print("📝 requirements.txt created")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="SmartRepo - AI-Powered Code Analysis and Documentation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python smartrepo_analyzer.py analyze ./my-project
  python smartrepo_analyzer.py analyze /path/to/project --output ./analysis
  python smartrepo_analyzer.py create-requirements
  python smartrepo_analyzer.py help
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a code project')
    analyze_parser.add_argument('project_path', help='Path to the project directory')
    analyze_parser.add_argument('--output', '-o', help='Output directory for generated files')
    analyze_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    analyze_parser.add_argument('--ai-key', type=str, help='OpenAI API key for smart summarization (optional)')
    analyze_parser.add_argument('--complexity', action='store_true', help='Enable detailed complexity analysis (slower)')

    # Create requirements command
    req_parser = subparsers.add_parser('create-requirements', help='Create requirements.txt file')

    # Help command
    help_parser = subparsers.add_parser('help', help='Show help and usage instructions')

    args = parser.parse_args()

    if args.command == 'analyze':
        analyzer = SmartRepoAnalyzer()
        analyzer.run(args.project_path, args.output, enable_complexity=args.complexity)
    elif args.command == 'create-requirements':
        create_requirements_txt()
    elif args.command == 'help' or args.command is None:
        print("\033[1;36m\nWelcome to SmartRepo!\033[0m")
        print("\033[1;33mAI-Powered Code Analysis and Documentation Tool\033[0m\n")
        print("Usage:")
        print("  python smartrepo_analyzer.py <command> [options]\n")
        print("Available commands:")
        print("  analyze <project_path>   Analyze a code project and generate reports")
        print("  create-requirements      Create requirements.txt file for dependencies")
        print("  help                     Show this help message\n")
        print("Options for 'analyze':")
        print("  --output, -o <dir>       Output directory for generated files")
        print("  --verbose, -v            Enable verbose output")
        print("  --ai-key <key>           OpenAI API key for smart summarization (optional)\n")
        print("Examples:")
        print("  python smartrepo_analyzer.py analyze ./my-project")
        print("  python smartrepo_analyzer.py analyze ./my-project --output ./analysis")
        print("  python smartrepo_analyzer.py analyze ./my-project --ai-key sk-...\n")
        print("For more details, see the README.md or run 'python smartrepo_analyzer.py help'\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
