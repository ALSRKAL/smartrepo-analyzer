import subprocess
from pathlib import Path
from typing import List, Dict
import json

def analyze_security_with_bandit(py_files: List[Path]) -> Dict[str, dict]:
    results = {}
    for file in py_files:
        proc = subprocess.run(['bandit', '-f', 'json', '-q', str(file)], capture_output=True, text=True)
        try:
            data = json.loads(proc.stdout)
            results[str(file)] = data.get('results', [])
        except Exception:
            continue
    return results 