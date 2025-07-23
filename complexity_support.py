import subprocess
from pathlib import Path
from typing import List, Dict
import json

def analyze_complexity_with_radon(py_files: List[Path]) -> Dict[str, dict]:
    results = {}
    for file in py_files:
        proc = subprocess.run(['radon', 'cc', '-s', '-j', str(file)], capture_output=True, text=True)
        try:
            data = json.loads(proc.stdout)
            results[str(file)] = data.get(str(file), [])
        except Exception:
            continue
    return results

def analyze_maintainability_with_radon(py_files: List[Path]) -> Dict[str, dict]:
    results = {}
    for file in py_files:
        proc = subprocess.run(['radon', 'mi', '-s', '-j', str(file)], capture_output=True, text=True)
        try:
            data = json.loads(proc.stdout)
            results[str(file)] = data.get(str(file), {})
        except Exception:
            continue
    return results 