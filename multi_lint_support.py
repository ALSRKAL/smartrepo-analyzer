import subprocess
from pathlib import Path
from typing import List, Dict

def run_flake8_on_files(files: List[Path]) -> List[Dict]:
    results = []
    for file in files:
        proc = subprocess.run([
            'flake8', str(file), '--format=%(row)d:%(col)d:%(code)s:%(text)s'
        ], capture_output=True, text=True)
        for line in proc.stdout.strip().splitlines():
            parts = line.split(':', 3)
            if len(parts) == 4:
                row, col, code, text = parts
                results.append({'file': str(file), 'row': row, 'col': col, 'code': code, 'text': text})
    return results

def run_eslint_on_files(files: List[Path]) -> List[Dict]:
    results = []
    for file in files:
        proc = subprocess.run([
            'eslint', '--format', 'json', str(file)
        ], capture_output=True, text=True)
        try:
            import json
            lint_results = json.loads(proc.stdout)
            for res in lint_results:
                for msg in res.get('messages', []):
                    results.append({
                        'file': res.get('filePath'),
                        'line': msg.get('line'),
                        'ruleId': msg.get('ruleId'),
                        'message': msg.get('message'),
                        'severity': msg.get('severity')
                    })
        except Exception:
            continue
    return results 