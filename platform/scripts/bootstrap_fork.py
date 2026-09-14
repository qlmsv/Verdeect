#!/usr/bin/env python3
"""Fetch a pinned upstream checkout. No GitHub write and no deployment."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,default=ROOT/'.work/openwebui')
    args=p.parse_args();target=args.destination.resolve()
    lock=json.loads((ROOT/'upstream.lock.json').read_text())
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','clone','--branch',lock['tag'],'--depth','1','--single-branch',lock['repository'],str(target)],check=True)
        subprocess.run(['git','-C',str(target),'remote','rename','origin','upstream'],check=True)
        subprocess.run(['git','-C',str(target),'switch','-c','platform/m0-foundation'],check=True)
    subprocess.run([sys.executable,str(ROOT/'integrations/openwebui/apply_overlay.py'),str(target)],check=True)
    print('Prepared local fork checkout. Review git diff. Nothing has been pushed to GitHub.')
if __name__=='__main__':main()
