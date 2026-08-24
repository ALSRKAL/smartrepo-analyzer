"""Call-graph extraction and cycle detection for Python projects.

استخراج رسم نداءات الدوال (call graph) من ملفات Python واكتشاف
الدورات التبادلية، مع دعم اختياري لمكتبة networkx.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set

try:  # optional dependency – a pure-Python fallback is used when missing
    import networkx as nx
except ImportError:  # pragma: no cover - exercised only without networkx
    nx = None


def nx_available() -> bool:
    """True when networkx is installed (better cycle detection)."""
    return nx is not None


def extract_call_graph(py_files: List[Path]) -> Dict[str, Set[str]]:
    """Map ``file.py::function`` -> set of called function names.

    يستخرج العلاقات بين الدوال: كل دالة ومجموعة الدوال التي تستدعيها.
    """
    call_graph: Dict[str, Set[str]] = {}
    for file in py_files:
        try:
            tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue

        defined = {
            n.name
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls: Set[str] = set()
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        func = sub.func
                        if isinstance(func, ast.Name):
                            calls.add(func.id)
                        elif isinstance(func, ast.Attribute):
                            # self.method() -> record bare method name as well
                            calls.add(func.attr)
                # keep only project-local calls to reduce noise
                local_calls = calls & defined
                key = f"{file.name}::{node.name}"
                existing = call_graph.setdefault(key, set())
                existing.update(local_calls)
    return call_graph


def call_graph_to_mermaid(call_graph: Dict[str, Set[str]]) -> str:
    """Render the call graph as a Mermaid flowchart."""
    lines = ["graph TD"]
    for src, targets in call_graph.items():
        src_node = "F_" + _sanitize(src)
        if not targets:
            lines.append(f"    {src_node}['{src}']")
        for tgt in sorted(targets):
            tgt_node = "F_" + _sanitize(tgt)
            lines.append(f"    {src_node}('{src}') --> {tgt_node}('{tgt}')")
    return "\n".join(lines)


def _sanitize(name: str) -> str:
    """Make an arbitrary identifier safe for Mermaid node ids."""
    out = []
    for ch in name:
        out.append(ch if ch.isalnum() or ch == "_" else "_")
    sanitized = "".join(out)
    if not sanitized or sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized


def find_cycles(call_graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Detect circular call chains.

    يكتشف حلقات النداء التبادلية بين الدوال. تُحلّ أسماء الدوال المختصرة
    إلى مساراتها المؤهلة أولًا، ثم يُستخدم networkx إن وُجد وإلا فخوارزمية
    DFS خفيفة مدمجة.
    """
    # Resolve bare callee names to fully-qualified keys when unambiguous.
    by_name: Dict[str, List[str]] = {}
    for key in call_graph:
        bare = key.rsplit("::", 1)[-1]
        by_name.setdefault(bare, []).append(key)

    edges: Dict[str, Set[str]] = {}
    for src, targets in call_graph.items():
        out: Set[str] = set()
        for tgt in targets:
            candidates = by_name.get(tgt, [])
            if len(candidates) == 1:
                out.add(candidates[0])
            else:
                out.add(tgt)
        edges[src] = out

    if nx is not None:
        graph = nx.DiGraph()
        for src, tgts in edges.items():
            for tgt in tgts:
                graph.add_edge(src, tgt)
        try:
            return [list(c) for c in nx.simple_cycles(graph)]
        except Exception:
            pass
    return _find_cycles_dfs(edges)


def _find_cycles_dfs(edges: Dict[str, Set[str]]) -> List[List[str]]:
    """Tarjan-free simple cycle finder limited to small cycles (len<=8)."""
    cycles: List[List[tuple]] = []
    seen: set = set()
    MAX_LEN = 8

    def dfs(node: str, path: List[str], visited: Set[str]):
        for nxt in sorted(edges.get(node, ())):
            # map bare callee names back to fully-qualified nodes
            candidates = (
                [nxt] if nxt in edges else [k for k in edges if k.endswith("::" + nxt)]
            )
            for cand in candidates:
                if cand == path[0]:
                    cycle = tuple(path + [cand])
                    canon = tuple(sorted(set(cycle)))
                    if canon not in seen:
                        seen.add(canon)
                        cycles.append(list(dict.fromkeys(cycle)))
                elif cand not in visited and len(path) < MAX_LEN:
                    dfs(cand, path + [cand], visited | {cand})

    for start in sorted(edges):
        dfs(start, [start], {start})
    return cycles


def save_call_graph_mermaid(call_graph: Dict[str, Set[str]], output_path: Path):
    """Write the Mermaid rendering of the call graph to disk."""
    output_path.write_text(call_graph_to_mermaid(call_graph), encoding="utf-8")
