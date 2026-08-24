"""Mermaid class-diagram generation from Python sources.

توليد مخطط UML للكلاسات بصيغة Mermaid من ملفات Python، مع استخراج
الخصائص والدوال والعلاقات بين الكلاسات.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List


def _safe_name(name: str) -> str:
    return "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in name) or "Anon"


def generate_mermaid_class_diagram(py_files: List[Path], output_path: Path):
    """Write a Mermaid ``classDiagram`` describing all classes found.

    يستخرج الكلاسات وخصائصها ودوالها وعلاقات الوراثة، ويكتب المخطط
    إلى المسار المحدد.
    """
    classes: List[Dict] = []
    for file in py_files:
        try:
            tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [
                b.id for b in node.bases
                if isinstance(b, ast.Name)
            ] + [
                f"{b.value.id}.{b.attr}"
                for b in node.bases
                if isinstance(b, ast.Attribute) and isinstance(b.value, ast.Name)
            ]
            methods: List[str] = []
            attributes: List[str] = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    attributes.append(item.target.id)
                elif isinstance(item, ast.Assign):
                    for t in item.targets:
                        if isinstance(t, ast.Name):
                            attributes.append(t.id)
            classes.append(
                {
                    "name": node.name,
                    "bases": [b for b in bases if b],
                    "methods": methods,
                    "attributes": attributes,
                }
            )

    lines = ["classDiagram"]
    written_pairs = set()
    for cls in classes:
        cname = _safe_name(cls["name"])
        lines.append(f"    class {cname} {{")
        for attr in cls["attributes"][:10]:
            lines.append(f"        {_safe_name(attr)}")
        for m in cls["methods"][:15]:
            lines.append(f"        {_safe_name(m)}()")
        lines.append("    }")
        for base in cls["bases"]:
            pair = (_safe_name(base), cname)
            if pair not in written_pairs:
                written_pairs.add(pair)
                lines.insert(1, f"    {pair[0]} <|-- {cname}")

    output_path.write_text("\n".join(lines), encoding="utf-8")
