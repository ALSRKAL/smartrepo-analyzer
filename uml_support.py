import ast
from pathlib import Path
from typing import List

def generate_mermaid_class_diagram(py_files: List[Path], output_path: Path):
    """
    توليد مخطط Mermaid class diagram من ملفات Python
    """
    classes = []
    for file in py_files:
        try:
            tree = ast.parse(file.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    bases = [b.id if isinstance(b, ast.Name) else '' for b in node.bases]
                    classes.append((node.name, bases))
        except Exception:
            continue
    lines = ["classDiagram"]
    for cls, bases in classes:
        lines.append(f"    class {cls}")
        for base in bases:
            if base:
                lines.append(f"    {base} <|-- {cls}")
    output_path.write_text('\n'.join(lines), encoding='utf-8') 