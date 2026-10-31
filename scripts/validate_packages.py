#!/usr/bin/env python3
"""Verify finished packages on the runner BEFORE calling the shared publisher."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def validate():
    meta = json.loads((ROOT / '.work/build-meta.json').read_text(encoding='utf-8'))
    dist = ROOT / 'dist'
    expected = {meta['portable_zip'], meta['source_zip']}
    files = {p.name for p in dist.glob('*.zip')}
    if files != expected:
        raise RuntimeError(f'Unexpected packaged ZIPs {files!r}; expected exactly {expected!r}')
    for name in sorted(expected):
        archive = dist / name
        if not 0 < archive.stat().st_size < 2 * 1024**3:
            raise RuntimeError(f'Empty/oversize package: {name}')
        with zipfile.ZipFile(archive, 'r') as z:
            bad = z.testzip()
            if bad:
                raise RuntimeError(f'Corrupt ZIP member {bad!r} in {name}')
            entries = set(z.namelist())
            if name == meta['portable_zip']:
                needed = {'App/zyntax.exe', 'Launch-ZyntaxAI.cmd', 'ZyntaxAI-Manager.cmd',
                          'Data/.keep', 'RELEASE-METADATA.json', 'LICENSE.txt', 'SOURCE-CODE.txt'}
                if not needed.issubset(entries):
                    raise RuntimeError(f'Portable ZIP missing files: {needed - entries}')
                if z.read('App/zyntax.exe')[:2] != b'MZ':
                    raise RuntimeError('Portable ZIP lacks valid Windows executable header')
                data = json.loads(z.read('RELEASE-METADATA.json'))
                if data['tag'] != meta['tag']:
                    raise RuntimeError('Portable ZIP release metadata mismatch')
            else:
                needed = {'ZyntaxAI-patched-source/LICENSE',
                          'ZyntaxAI-patched-source/Cargo.lock',
                          'ZyntaxAI-patched-source/pnpm-lock.yaml',
                          'portable-builder/scripts/apply_portable.py'}
                if not needed.issubset(entries):
                    raise RuntimeError(f'GPL source archive missing files: {needed - entries}')
        print(f'Validated {name}: sha256={hashlib.sha256(archive.read_bytes()).hexdigest()}')
    print('All ZIP CRCs and expected contents validated. Publisher will independently hash/check/upload.')


if __name__ == '__main__':
    try:
        validate()
    except (RuntimeError, ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        sys.exit(f'ERROR validating ZIPs: {error}')
