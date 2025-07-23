import subprocess
from pathlib import Path
from typing import List, Dict
import tempfile
import shutil

def get_contributors(repo_path: Path) -> List[Dict]:
    """
    إرجاع قائمة المساهمين وعدد الكوميتات لكل واحد
    """
    try:
        result = subprocess.run([
            'git', '-C', str(repo_path), 'shortlog', '-s', '-n', '--all', '--no-merges'
        ], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().splitlines()
        contributors = []
        for line in lines:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                commits, name = parts
                contributors.append({'name': name.strip(), 'commits': int(commits.strip())})
        return contributors
    except Exception:
        return []

def clone_repo_temp(git_url: str) -> Path:
    """
    استنساخ مستودع git في مجلد مؤقت وإرجاع المسار
    """
    tmpdir = Path(tempfile.mkdtemp())
    subprocess.run(['git', 'clone', '--depth', '1', git_url, str(tmpdir)], check=True)
    return tmpdir

def cleanup_temp_repo(tmpdir: Path):
    shutil.rmtree(tmpdir, ignore_errors=True) 