"""Pylint integration (batched).

تشغيل أداة pylint على دفعات من الملفات بدلًا من عملية لكل ملف.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List

from tool_runner import DEFAULT_BATCH_SIZE, run_command, tool_available


def run_pylint_on_files(
    files: List[Path], batch_size: int = DEFAULT_BATCH_SIZE
) -> List[Dict]:
    """Run pylint once per batch and merge JSON reports.

    يعيد قائمة بالتحذيرات والأخطاء التي اكتشفها pylint.
    """
    results: List[Dict] = []
    if not files or not tool_available("pylint"):
        return results

    def parse(proc: subprocess.CompletedProcess, batch: List[Path]):
        try:
            items = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            return
        for item in items:
            if isinstance(item, dict):
                results.append(item)

    def build_cmd(batch: List[Path]) -> List[str]:
        return ["pylint", "--output-format=json", "--score=n", *[str(f) for f in batch]]

    for start in range(0, len(files), batch_size):
        batch = files[start : start + batch_size]
        proc = run_command(build_cmd(batch))
        # pylint exits non-zero whenever it emits messages; that is expected.
        if proc is not None:
            parse(proc, batch)
    return results
