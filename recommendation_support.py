"""Smart, context-aware recommendations for improving a codebase.

مولد التوصيات الذكية: يحلل المقاييس ويقترح تحسينات عملية مرتبة
حسب الأولوية، مع دعم السياق الكامل للمشروع.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def generate_recommendations(
    metrics: Dict,
    coverage: Optional[float] = None,
    lint_issues: Optional[int] = None,
    security_issues: Optional[Dict] = None,
    test_ratio: Optional[float] = None,
) -> List[str]:
    """Return prioritized bilingual (EN) recommendations.

    يقبل المقاييس الأساسية وسياقات اختيارية (أمان، نسبة اختبارات)
    ويولّد توصيات عملية. الدالة متوافقة رجعيًا مع الاستدعاء القديم.
    """
    recs: List[str] = []
    avg_complexity = metrics.get("average_complexity", 0) or 0
    total_lines = metrics.get("total_lines", 0) or 0
    total_files = max(metrics.get("total_files", 1), 1)

    if avg_complexity > 10:
        recs.append("[HIGH] Very high average complexity (%.1f). Refactor the most complex functions into smaller units." % avg_complexity)
    elif avg_complexity > 5:
        recs.append("[MEDIUM] Above-average complexity (%.1f). Consider splitting large conditionals." % avg_complexity)

    if total_lines > 50000:
        recs.append("[MEDIUM] Large codebase (%s lines). Consider modularizing into packages." % f"{total_lines:,}")

    if coverage is not None and coverage < 60:
        recs.append(f"[HIGH] Test coverage is {coverage:.1f}% (<60%). Add tests for critical paths.")

    if lint_issues is not None and lint_issues > 20:
        density = lint_issues / total_files
        recs.append(f"[MEDIUM] {lint_issues} linting issues (~{density:.0f}/file). Run an auto-formatter and fix recurring patterns.")

    func_density = (metrics.get("total_functions", 0) or 0) / total_files
    if func_density > 15:
        recs.append(f"[LOW] High function density ({func_density:.0f}/file). Distribute responsibilities across modules.")

    if security_issues:
        high = security_issues.get("HIGH", 0)
        med = security_issues.get("MEDIUM", 0)
        if high:
            recs.append(f"[CRITICAL] {high} HIGH-severity security issues found. Review bandit report immediately.")
        elif med:
            recs.append(f"[MEDIUM] {med} medium-severity security findings. Check security_report.json.")

    if test_ratio is not None:
        if test_ratio == 0:
            recs.append("[HIGH] No tests detected at all. Start with unit tests for core logic.")
        elif test_ratio < 0.1:
            recs.append("[MEDIUM] Only %.0f%% of files are tests. Aim for >20%%." % (test_ratio * 100))

    if not recs:
        recs.append("[OK] Codebase looks healthy — keep up the good work!")
    return recs
