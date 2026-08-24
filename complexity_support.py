"""Cyclomatic complexity and maintainability analysis via radon.

تحليل التعقيد السيكلومي وقابلية الصيانة باستخدام أداة radon،
بتشغيل واحد لكل دفعة ملفات بدلًا من عملية منفصلة لكل ملف.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from tool_runner import DEFAULT_BATCH_SIZE, run_command, tool_available


def analyze_complexity_with_radon(
    py_files: List[Path], batch_size: int = DEFAULT_BATCH_SIZE
) -> Dict[str, dict]:
    """Return ``{file_path: [block_info, ...]}`` using batched radon calls.

    يحلل تعقيد ملفات Python دفعة واحدة. إذا لم تكن radon مثبتة يُعاد قاموس فارغ.
    """
    results: Dict[str, dict] = {}
    if not py_files or not tool_available("radon"):
        return results

    def parse(proc, batch):
        try:
            data = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            return
        for path in batch:
            key = str(path)
            if key in data:
                results[key] = data[key]

    for start in range(0, len(py_files), batch_size):
        batch = py_files[start : start + batch_size]
        proc = run_command(["radon", "cc", "-s", "-j", *[str(f) for f in batch]])
        if proc is not None:
            parse(proc, batch)
    return results


def analyze_maintainability_with_radon(
    py_files: List[Path], batch_size: int = DEFAULT_BATCH_SIZE
) -> Dict[str, dict]:
    """Return ``{file_path: {"mi": score, "rank": letter}}`` per file.

    يقيس مؤشر قابلية الصيانة (Maintainability Index) لملفات Python.
    """
    results: Dict[str, dict] = {}
    if not py_files or not tool_available("radon"):
        return results

    def parse(proc, batch):
        try:
            data = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            return
        for path in batch:
            key = str(path)
            if key not in data:
                continue
            entry = data[key]
            if isinstance(entry, list) and entry and isinstance(entry[0], dict):
                # radon MI JSON: [{"mi": float, "rank": str}]
                results[key] = {"mi": entry[0].get("mi"), "rank": entry[0].get("rank")}
            elif isinstance(entry, dict):
                results[key] = entry
            elif isinstance(entry, (int, float)):
                results[key] = {"mi": entry}

    for start in range(0, len(py_files), batch_size):
        batch = py_files[start : start + batch_size]
        proc = run_command(["radon", "mi", "-s", "-j", *[str(f) for f in batch]])
        if proc is not None:
            parse(proc, batch)
    return results


def summarize_complexity(complexity: Dict[str, dict]) -> Dict[str, object]:
    """Aggregate raw radon output into compact statistics.

    يلخص نتائج radon الخام إلى إحصاءات موجزة سهلة العرض.
    """
    total_blocks = 0
    total_complexity = 0
    worst_blocks: List[Dict[str, object]] = []
    for file_path, blocks in complexity.items():
        if isinstance(blocks, str):
            continue
        for block in blocks:
            cc = block.get("complexity", 0)
            total_blocks += 1
            total_complexity += cc
            worst_blocks.append(
                {
                    "file": file_path,
                    "name": block.get("name", "?"),
                    "line": block.get("lineno", 0),
                    "complexity": cc,
                    "rank": block.get("rank", ""),
                }
            )
    worst_blocks.sort(key=lambda b: b["complexity"], reverse=True)
    avg = round(total_complexity / total_blocks, 2) if total_blocks else 0.0
    return {
        "total_functions": total_blocks,
        "average_complexity": avg,
        "highest_complexity": worst_blocks[:10],
    }
