"""flake8 and eslint integrations (batched).

تشغيل أدوات flake8 و eslint على دفعات من الملفات لتحسين الأداء.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from tool_runner import DEFAULT_BATCH_SIZE, run_command, tool_available


def run_flake8_on_files(
    files: List[Path], batch_size: int = DEFAULT_BATCH_SIZE
) -> List[dict]:
    """Run flake8 once per batch and parse ``line:col:code:text`` output.

    يعيد قائمة بمشاكل التنسيق والأسلوب التي يكتشفها flake8.
    """
    results: List[dict] = []
    if not files or not tool_available("flake8"):
        return results

    def build_cmd(batch: List[Path]) -> List[str]:
        return [
            "flake8",
            "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s",
            *[str(f) for f in batch],
        ]

    for start in range(0, len(files), batch_size):
        batch = files[start : start + batch_size]
        proc = run_command(build_cmd(batch))
        if proc is None:
            continue
        for line in (proc.stdout or "").splitlines():
            # path may itself contain ':' on Windows; split from the right.
            parts = line.split(":", 3)
            if len(parts) == 4:
                path, row, col, text = parts[0], parts[1], parts[2], parts[3]
                code, _, message = text.partition(":")
                results.append(
                    {
                        "file": path,
                        "row": row,
                        "col": col,
                        "code": code.strip(),
                        "text": message.strip() or text.strip(),
                    }
                )
    return results


def run_eslint_on_files(
    files: List[Path], batch_size: int = DEFAULT_BATCH_SIZE
) -> List[dict]:
    """Run eslint once per batch and merge JSON reports.

    يعيد قائمة بمشاكل جودة كود JavaScript/TypeScript.
    """
    results: List[dict] = []
    if not files or not tool_available("eslint"):
        return results

    def build_cmd(batch: List[Path]) -> List[str]:
        return ["eslint", "--format", "json", "--no-error-on-unmatched-pattern", *[str(f) for f in batch]]

    for start in range(0, len(files), batch_size):
        batch = files[start : start + batch_size]
        proc = run_command(build_cmd(batch))
        if proc is None:
            continue
        try:
            lint_results = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            continue
        for res in lint_results:
            for msg in res.get("messages", []):
                results.append(
                    {
                        "file": res.get("filePath"),
                        "line": msg.get("line"),
                        "column": msg.get("column"),
                        "ruleId": msg.get("ruleId"),
                        "message": msg.get("message"),
                        "severity": msg.get("severity"),
                    }
                )
    return results
