import ast
from pathlib import Path
from typing import List

def extract_usage_examples(py_files: List[Path]) -> List[str]:
    """
    استخراج أمثلة استخدام من ملفات Python (من دوال test_ أو docstrings)
    """
    examples = []
    for file in py_files:
        try:
            tree = ast.parse(file.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                # أمثلة من دوال test_
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    examples.append(f"من {file.name}: {node.name}() -> {ast.get_docstring(node) or ''}")
                # أمثلة من docstring للكلاس أو الدالة
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node)
                    if doc and 'example' in doc.lower():
                        examples.append(f"من {file.name}: {node.name} -> {doc}")
        except Exception:
            continue
    return examples 