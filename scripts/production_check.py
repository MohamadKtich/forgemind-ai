from __future__ import annotations
import os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
checks=[]
def add(name,ok,detail): checks.append((name,ok,detail))
env=ROOT/'backend/.env'
add('backend/.env exists',env.exists(),str(env))
if env.exists():
    text=env.read_text(errors='ignore')
    add('no default SECRET_KEY','change-this-local-secret-before-deployment' not in text,'replace default secret')
    add('seed disabled','SEED_DEFAULT_USERS=false' in text.lower().replace(' ',''),'set false for production')
    add('registration reviewed','ALLOW_LOCAL_REGISTRATION=false' in text.lower().replace(' ',''),'set false for production')
add('Alembic configured',(ROOT/'alembic.ini').exists(),'alembic.ini')
add('model notebooks',len(list((ROOT/'notebooks').glob('*.ipynb')))>=2,'notebooks/')
for name,ok,detail in checks: print(('PASS' if ok else 'FAIL'),name,'-',detail)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
