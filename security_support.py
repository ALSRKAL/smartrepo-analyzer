"""Security analysis via bandit (batched for speed).

تحليل أمني باستخدام أداة bandit بتشغيل واحد لكل دفعة ملفات.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from tool_runner import DEFAULT_BATCH_SIZE, run_command, tool_available

# Severity levels bandit may report.
SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


def analyze_security_with_bandit(
    py_files: List[Path], batch_size: int = DEFAULT_BATCH_SIZE
) -> Dict[str, list]:
    """Return ``{file_path: [issue, ...]}`` for all Python files.

    يفحص ملفات Python بحثًا عن ثغرات أمنية معروفة. يعيد قاموسًا فارغًا
    إذا لم تكن الأداة مثبتة.
    """
    results: Dict[str, list] = {}
    if not py_files or not tool_available("bandit"):
        return results

    def parse(proc, batch):
        try:
            data = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            return
        by_file = {}
        for issue in data.get("results", []):
            filename = issue.get("filename", "")
            by_file.setdefault(filename, []).append(issue)
        # Map back to the exact paths we passed in (bandit normalizes paths).
        resolved = {str(Path(f).resolve()): f for f in batch}
        norm_map = {str(Path(k)): k for k in resolved}
        for path in batch:
            key = str(path)
            norm_key = str(Path(path))
            found = None
            for bkey, issues in by_file.items():
                if str(Path(bkey)) == norm_key:
                    found = issues
                    break
            if found is not None:
                results[key] = found
            elif key not in results:
                results[key] = []

    for start in range(0, len(py_files), batch_size):
        batch = py_files[start : start + batch_size]
        proc = run_command(
            ["bandit", "-f", "json", "-q", *[str(f) for f in batch]]
        )
        if proc is not None:
            parse(proc, batch)
    return results


def summarize_security(security: Dict[str, list]) -> Dict[str, int]:
    """Count issues grouped by severity.

    يلخص عدد المشاكل الأمنية حسب درجة الخطورة.
    """
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "total": 0}
    for issues in security.values():
        for issue in issues:
            sev = str(issue.get("issue_severity", "LOW")).upper()
            counts[sev] = counts.get(sev, 0) + 1
            counts["total"] += 1
    return counts
