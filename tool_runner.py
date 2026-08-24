"""Shared helpers for running external tools efficiently.

Instead of spawning one subprocess per file (which is extremely slow on
large projects), tools are invoked once per *batch* of files.

يحتوي هذا الملف على أدوات مساعدة لتشغيل الأدوات الخارجية بكفاءة عالية،
حيث يتم تشغيل كل أداة مرة واحدة لكل دفعة من الملفات بدلًا من عملية
منفصلة لكل ملف، مما يحسّن الأداء بشكل كبير.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

# Number of files per external-tool invocation. Keeps command lines well
# below OS length limits even for huge repositories.
DEFAULT_BATCH_SIZE = 64

_TOOL_CACHE: dict = {}


def tool_available(name: str) -> bool:
    """Return True if an executable exists (result cached).

    للتحقق من توفر أداة خارجية في النظام (مع تخزين النتيجة مؤقتًا).
    """
    if name not in _TOOL_CACHE:
        _TOOL_CACHE[name] = shutil.which(name) is not None
    return _TOOL_CACHE[name]


def reset_tool_cache() -> None:
    """Clear cached tool lookups (useful in tests)."""
    _TOOL_CACHE.clear()


def run_command(cmd: Sequence[str], timeout: int = 300) -> Optional[subprocess.CompletedProcess]:
    """Run a command safely; returns None when the executable is missing.

    تنفيذ أمر خارجي بأمان مع مهلة زمنية، ويعيد None إذا كانت الأداة غير مثبتة.
    """
    try:
        return subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return None


def run_batched(
    files: List[Path],
    build_cmd: Callable[[List[Path]], List[str]],
    batch_size: int = DEFAULT_BATCH_SIZE,
    parse: Optional[Callable[[subprocess.CompletedProcess, List[Path]], None]] = None,
) -> List[subprocess.CompletedProcess]:
    """Run ``build_cmd(batch)`` once per chunk of files.

    تشغيل الأمر على دفعات من الملفات لتقليل عدد العمليات (subprocess)
    وتسريع التحليل بشكل ملحوظ.
    """
    results: List[subprocess.CompletedProcess] = []
    if not files:
        return results
    for start in range(0, len(files), batch_size):
        batch = files[start : start + batch_size]
        proc = run_command(build_cmd(batch))
        if proc is not None and parse is not None:
            parse(proc, batch)
        if proc is not None:
            results.append(proc)
    return results


def chunked(items: Iterable[Path], size: int = DEFAULT_BATCH_SIZE) -> Iterable[List[Path]]:
    """Yield lists of at most ``size`` items."""
    batch: List[Path] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
