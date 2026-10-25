"""Small dependency-free release scan; not a substitute for external review."""
from pathlib import Path
import re
import sys
root = Path(__file__).resolve().parents[1]
patterns = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{30,}', r'AKIA[0-9A-Z]{16}', r'sk-(?:proj-)?[A-Za-z0-9_-]{30,}']
blocked = {'.git','.venv','node_modules','dist','__pycache__','.pytest_cache','data'}
findings=[]
for p in root.rglob('*'):
    if not p.is_file() or any(part in blocked for part in p.relative_to(root).parts):continue
    if p.suffix == '.bundle':continue
    if p.name == '.env' or (p.name.startswith('.env.') and p.name != '.env.example'):
        findings.append(f'Private environment file in release tree: {p.relative_to(root)}');continue
    try:content=p.read_text()
    except (UnicodeDecodeError,OSError):continue
    for pattern in patterns:
        if re.search(pattern,content):findings.append(f'Possible credential: {p.relative_to(root)}')
    if re.search(r'/U[s]ers/[^/]+/',content):
        findings.append(f'Possible personal identifier: {p.relative_to(root)}')
if findings:
    print('\n'.join(findings));sys.exit(1)
print('Release source scan passed: no matched credential patterns, private env files or personal paths.')
