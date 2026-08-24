"""Extract usage examples from docstrings and test functions.

استخراج أمثلة الاستخدام من ملفات Python: من دوال الاختبار ومن
الـ docstrings التي تحتوي على كود توضيحي.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List


def extract_usage_examples(py_files: List[Path]) -> List[str]:
    """Collect examples from ``test_*`` functions and example docstrings.

    يعيد قائمة أسطر تصف أمثلة الاستخدام المكتشفة في المشروع.
    """
    examples: List[str] = []
    for file in py_files:
        try:
            tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                doc = ast.get_docstring(node) or ""
                first = doc.strip().splitlines()[0] if doc.strip() else ""
                examples.append(f"From {file.name}: {node.name}()  {first}".rstrip())
            doc = ast.get_docstring(node)
            if doc and "example" in doc.lower() and ">>>" in doc:
                # pull the doctest lines themselves
                snippets = [ln for ln in doc.splitlines() if ln.strip().startswith(">>>")]
                if snippets:
                    joined = " | ".join(s.strip().lstrip(">").strip() for s in snippets[:3])
                    examples.append(f"From {file.name}: {node.name} -> {joined}")
    return examples
