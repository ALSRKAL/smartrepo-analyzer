import ast
from pathlib import Path
from typing import List, Dict, Set
import networkx as nx

def extract_call_graph(py_files: List[Path]) -> Dict[str, Set[str]]:
    """
    استخراج call graph: دالة -> الدوال التي تستدعيها
    """
    call_graph = {}
    for file in py_files:
        try:
            tree = ast.parse(file.read_text(encoding='utf-8'))
            funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
            for func_name, func_node in funcs.items():
                calls = set()
                for node in ast.walk(func_node):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        calls.add(node.func.id)
                call_graph[f"{file.name}:{func_name}"] = calls
        except Exception:
            continue
    return call_graph

def call_graph_to_mermaid(call_graph: Dict[str, Set[str]]) -> str:
    lines = ["graph TD"]
    for src, tgts in call_graph.items():
        src_node = src.replace(":", "_")
        if not tgts:
            lines.append(f"    {src_node}['{src}']")
        for tgt in tgts:
            tgt_node = tgt.replace(":", "_")
            lines.append(f"    {src_node}['{src}'] --> {tgt_node}['{tgt}']")
    return '\n'.join(lines)

def find_cycles(call_graph: Dict[str, Set[str]]) -> List[List[str]]:
    G = nx.DiGraph()
    for src, tgts in call_graph.items():
        for tgt in tgts:
            G.add_edge(src, tgt)
    return list(nx.simple_cycles(G))

def save_call_graph_mermaid(call_graph: Dict[str, Set[str]], output_path: Path):
    mermaid = call_graph_to_mermaid(call_graph)
    output_path.write_text(mermaid, encoding='utf-8') 