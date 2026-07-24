#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import re, sys
ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git','node_modules','.next','.venv','venv','__pycache__','.pytest_cache'}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'Supabase service key': re.compile(r'(?i)(service_role|supabase_service_role)\s*[=:]\s*["\']?eyJ'),
    'live database URL': re.compile(r'(?i)postgres(?:ql)?(?:\+psycopg)?://[^\s:<]+:[^\s@\[\]]+@'),
    'OpenAI key': re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b'),
}
PLACEHOLDERS = ('PROJECT_REF','ENCODED_PASSWORD','YOUR_PASSWORD','POOLER_HOST','example.com','localhost')
issues=[]
for path in ROOT.rglob('*'):
    if not path.is_file() or any(part in SKIP for part in path.parts): continue
    if path.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.joblib','.pdf','.zip'}: continue
    try: text=path.read_text(encoding='utf-8',errors='ignore')
    except OSError: continue
    for line_no,line in enumerate(text.splitlines(),1):
        for label, pattern in PATTERNS.items():
            if pattern.search(line):
                if label == 'live database URL' and any(token in line for token in PLACEHOLDERS):
                    continue
                issues.append((path.relative_to(ROOT),line_no,label))
if issues:
    for path,line,label in issues: print(f'[FAIL] {label}: {path}:{line}')
    sys.exit(1)
print('[OK] No obvious committed secrets found.')
