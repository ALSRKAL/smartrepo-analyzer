"""Git helpers: contributors and temporary repository cloning.

أدوات مساعدة لـ Git: إحصاء المساهمين واستنساخ المستودعات مؤقتًا.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from tool_runner import run_command


def get_contributors(repo_path: Path) -> List[Dict]:
    """Return ``[{"name": ..., "commits": n}, ...]`` sorted by commit count.

    يعيد قائمة المساهمين مع عدد الكوميتات لكل واحد، مرتبة تنازليًا.
    تعيد قائمة فارغة إذا لم يكن المجلد مستودع Git.
    """
    if not (Path(repo_path) / ".git").exists():
        return []
    result = run_command(
        ["git", "-C", str(repo_path), "shortlog", "-s", "-n", "--all", "--no-merges"],
        timeout=60,
    )
    if result is None or result.returncode != 0:
        return []
    contributors: List[Dict] = []
    for line in (result.stdout or "").strip().splitlines():
        parts = line.strip().split("\t", 1)
        if len(parts) == 2:
            try:
                commits = int(parts[0].strip())
            except ValueError:
                continue
            name = parts[1].strip()
            # shortlog may prefix emails: "name <email>"
            name = name.split("<")[0].strip() or "unknown"
            contributors.append({"name": name, "commits": commits})
    return contributors


def clone_repo_temp(git_url: str, depth: int = 1) -> Optional[Path]:
    """Shallow-clone a remote repository into a temp directory.

    يستنسخ مستودعًا بعيدًا إلى مجلد مؤقت (استنساخ سطحي للسرعة).
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="smartrepo-"))
    try:
        proc = run_command(
            ["git", "clone", f"--depth={depth}", git_url, str(tmpdir)],
            timeout=300,
        )
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    if proc is None or proc.returncode != 0:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    return tmpdir


def cleanup_temp_repo(tmpdir: Path):
    """Delete the temporary clone."""
    shutil.rmtree(tmpdir, ignore_errors=True)


def get_git_stats(repo_path: Path) -> Dict[str, Optional[str]]:
    """Collect lightweight repo stats: last commit date and total commits.

    يجمع إحصاءات سريعة عن المستودع: تاريخ آخر كوميت وإجمالي الكوميتات.
    """
    stats: Dict[str, Optional[str]] = {"last_commit": None, "total_commits": None}
    if not (Path(repo_path) / ".git").exists():
        return stats
    last = run_command(
        ["git", "-C", str(repo_path), "log", "-1", "--format=%cs"], timeout=30
    )
    if last is not None and last.returncode == 0:
        stats["last_commit"] = (last.stdout or "").strip() or None
    count = run_command(
        ["git", "-C", str(repo_path), "rev-list", "--count", "--all"], timeout=60
    )
    if count is not None and count.returncode == 0:
        stats["total_commits"] = (count.stdout or "").strip() or None
    return stats
