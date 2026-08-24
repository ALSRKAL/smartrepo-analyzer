"""Fast heuristic summarization of source files.

تلخيص سريع للملفات: أول وآخر الأسطر مع أسماء الدوال والكلاسات،
مع دعم أفضل لملفات Python عبر شجرة AST.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List


def summarize_file(file_path: Path, max_lines: int = 20) -> str:
    """Build a quick preview of a file (head, definitions, tail).

    ينتج ملخصًا نصيًا سريعًا لأي ملف مصدري مناسب للمعاينة البشرية.
    """
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    if len(lines) <= max_lines:
        return "\n".join(lines)

    suffix = file_path.suffix.lower()
    summary: List[str] = []
    if suffix == ".py":
        try:
            tree = ast.parse("\n".join(lines))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    summary.append(f"[{node.lineno}] def {node.name}()")
                elif isinstance(node, ast.ClassDef):
                    summary.append(f"[{node.lineno}] class {node.name}")
                elif hasattr(ast, "AsyncFunctionDef") and isinstance(node, ast.AsyncFunctionDef):
                    summary.append(f"[{node.lineno}] async def {node.name}()")
            doc = ast.get_docstring(tree)
            if doc:
                first_doc_line = doc.strip().splitlines()[0]
                summary.insert(0, f'docstring: "{first_doc_line}"')
            return "\n".join(lines[:5] + ["..."] + summary + ["...", *lines[-3:]])
        except (SyntaxError, ValueError):
            pass  # fall through to regex mode

    # Generic regex fallback for non-Python files
    defs = [
        f"[{i}] {line.strip()}"
        for i, line in enumerate(lines, start=1)
        if re.match(r"\s*(def |class |function |func |public |private )", line)
    ]
    return "\n".join(lines[:5] + ["..."] + defs[:30] + ["...", *lines[-3:]])
