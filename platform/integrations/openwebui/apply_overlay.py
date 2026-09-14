#!/usr/bin/env python3
"""Assemble a reviewable frontend fork, preserving the upstream Git checkout.

Moves existing route files into a route group without changing their URLs.
The upstream root layout then belongs only to chat routes; platform-only users
can bootstrap the independent shell without an OpenWebUI account. Crossing
these layout boundaries currently uses full document navigation.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def source_digest(root: Path = ROOT) -> str:
    selected=[]
    for folder in ["packages/platform-ui/src", "packages/ui-sdk/src", "modules/metering-ui/src", "integrations/openwebui/host", "integrations/openwebui/routes"]:
        selected.extend(p for p in (root/folder).rglob('*') if p.is_file())
    h=hashlib.sha256()
    for p in sorted(selected):
        h.update(str(p.relative_to(root)).encode());h.update(b"\0");h.update(p.read_bytes())
    return h.hexdigest()


def rewrite_root_imports(text: str) -> str:
    # Only loose files moved one level deeper need rebasing. Nested directories
    # move as a whole; $lib imports and generated ./$types retain their meaning.
    text=re.sub(r"((?:from|import)\s*['\"])(\.\./[^'\"]+)(['\"])", lambda m:m[1]+"../"+m[2]+m[3], text)
    return re.sub(r"(import\(\s*['\"])(\.\./[^'\"]+)(['\"])",lambda m:m[1]+"../"+m[2]+m[3],text)


def apply_overlay(checkout: Path, lock: dict, source: Path = ROOT) -> dict:
    marker=checkout/'.verdeect-overlay.json'
    fingerprint=source_digest(source)
    if marker.exists():
        previous=json.loads(marker.read_text())
        if previous['source_digest'] != fingerprint:
            raise RuntimeError('Overlay changed. Apply to a fresh pinned checkout; existing changes are never overwritten.')
        for relative,checksum in previous['generated'].items():
            path=checkout/relative
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:
                raise RuntimeError(f'Generated file was modified: {relative}. Refusing to overwrite.')
        return previous
    routes=checkout/'src/routes'
    layout=routes/'+layout.svelte'
    if not layout.exists() or git_blob(layout.read_bytes())!=lock['root_layout_blob']:
        raise RuntimeError('Upstream root layout does not match the pinned blob. Review a new release before applying.')
    for reserved in [routes/'(upstream)',routes/'_platform',checkout/'src/lib/platform']:
        if reserved.exists(): raise RuntimeError(f'Reserved path already exists: {reserved}')
    with tempfile.TemporaryDirectory(prefix='verdeect-overlay-',dir=checkout.parent) as temporary:
        staging=Path(temporary)
        staged_routes=staging/'routes';group=staged_routes/'(upstream)'
        shutil.copytree(routes,group)
        for p in group.iterdir():
            if p.is_file() and p.suffix in {'.svelte','.ts','.js'}:
                p.write_text(rewrite_root_imports(p.read_text()))
        shutil.copytree(source/'integrations/openwebui/host',staged_routes,dirs_exist_ok=True)
        shutil.copytree(source/'integrations/openwebui/routes',staged_routes,dirs_exist_ok=True)
        platform=staging/'platform'
        shutil.copytree(source/'packages/platform-ui/src',platform)
        shutil.copytree(source/'packages/ui-sdk/src',platform/'sdk')
        shutil.copytree(source/'modules/metering-ui/src',platform/'modules/metering')
        generated={}
        for path in platform.rglob('*'):
            if path.is_file():generated['src/lib/platform/'+str(path.relative_to(platform))]=hashlib.sha256(path.read_bytes()).hexdigest()
        for path in staged_routes.rglob('*'):
            if path.is_file() and '(upstream)' not in path.relative_to(staged_routes).parts:
                generated['src/routes/'+str(path.relative_to(staged_routes))]=hashlib.sha256(path.read_bytes()).hexdigest()
        report={'upstream_commit':lock['commit'],'overlay_version':lock['overlay_version'],
                'source_digest':fingerprint,'generated':generated,'production_ready':False}
        backup=staging/'original-routes'
        destination=checkout/'src/lib/platform'
        destination.parent.mkdir(parents=True,exist_ok=True)
        routes.rename(backup)
        try:
            staged_routes.rename(routes);platform.rename(destination)
            marker.write_text(json.dumps(report,indent=2)+'\n')
        except Exception:
            if routes.exists():shutil.rmtree(routes)
            backup.rename(routes)
            if destination.exists():shutil.rmtree(destination)
            if marker.exists():marker.unlink()
            raise
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout',type=Path)
    args=parser.parse_args()
    checkout=args.checkout.resolve()
    lock=json.loads((ROOT/'upstream.lock.json').read_text())
    if not (checkout/'.verdeect-overlay.json').exists():
        commit=subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()
        if commit!=lock['commit']:raise SystemExit('Wrong upstream commit. Use bootstrap_fork.py.')
        dirty=subprocess.check_output(['git','-C',str(checkout),'status','--porcelain'],text=True).strip()
        if dirty:raise SystemExit('Checkout is not clean. Commit or save your work before applying the overlay.')
    report=apply_overlay(checkout,lock)
    print(json.dumps({'checkout':str(checkout),'generated_files':len(report['generated']),'full_build_verified':False},indent=2))

if __name__=='__main__':main()
