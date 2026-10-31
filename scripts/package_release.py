#!/usr/bin/env python3
"""Package only the compiled portable Windows executable, plus full corresponding GPL source."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.work'
DIST = ROOT / 'dist'
SOURCE = WORK / 'upstream'
IGNORE_FOLDERS = {'.git', 'target', 'node_modules', 'dist', '.next', '.turbo', '__pycache__'}
IGNORE_SUFFIXES = {'.pyc', '.pyo'}


def load_meta():
    return json.loads((WORK / 'build-meta.json').read_text(encoding='utf-8'))


def add_file(archive, source: Path, target: str):
    if not source.is_file() or source.is_symlink():
        raise RuntimeError(f'File not found or symbolic link: {source}')
    archive.write(source, target)


def source_files(folder: Path):
    for p in sorted(folder.rglob('*')):
        if not p.is_file() or p.is_symlink():
            continue
        relative = p.relative_to(folder)
        if any(part in IGNORE_FOLDERS for part in relative.parts) or p.suffix in IGNORE_SUFFIXES:
            continue
        yield p, relative


def package():
    meta = load_meta()
    exe_candidates = [SOURCE / 'target/release/zyntax.exe', SOURCE / 'src-tauri/target/release/zyntax.exe']
    actual = [p for p in exe_candidates if p.is_file()]
    if len(actual) != 1:
        raise RuntimeError('Expected exactly one compiled zyntax.exe; found ' + repr([str(p) for p in actual]))
    exe = actual[0]
    with exe.open('rb') as handle:
        header = handle.read(2)
    if exe.stat().st_size < 100_000 or header != b'MZ':
        raise RuntimeError('EXE has invalid size or does not have a Windows PE header')
    if not (SOURCE / 'LICENSE').is_file():
        raise RuntimeError('GPL license not found in resolved official source')
    DIST.mkdir(exist_ok=True)
    if list(DIST.glob('*.zip')):
        raise RuntimeError('Unexpected preexisting ZIPs in dist; refusing to mix releases')
    portable_file = DIST / meta['portable_zip']
    source_file = DIST / meta['source_zip']
    source_notice = (
        'UNOFFICIAL ZyntaxAI Windows native portable build.\n'
        f"Upstream project: https://github.com/{meta['upstream']}\n"
        f"Stable tag: {meta['upstream_tag']}\n"
        f"Exact upstream commit: {meta['upstream_commit']}\n"
        f"Builder revision: {meta['revision']}\n"
        f"Portable release: {meta['tag']}\n"
        'License: GPL-3.0-or-later (see LICENSE.txt)\n'
        f"Complete patched corresponding source: {meta['source_zip']} (same GitHub release)\n"
        'Build process is documented in the independent builder repository.\n'
    )
    with zipfile.ZipFile(portable_file, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        add_file(z, exe, 'App/zyntax.exe')
        add_file(z, SOURCE / 'LICENSE', 'LICENSE.txt')
        for filename in ['Launch-ZyntaxAI.cmd', 'ZyntaxAI-Manager.cmd', 'README-PORTABLE.txt']:
            add_file(z, ROOT / 'runtime' / filename, filename)
        z.writestr('Data/.keep', 'This directory contains your settings, credentials, history and caches. Never overwrite it during upgrades.\n')
        z.writestr('SOURCE-CODE.txt', source_notice)
        z.writestr('RELEASE-METADATA.json', json.dumps(meta, indent=2) + '\n')
    # GPL corresponding source, including *patched* code, original license and builder recipe.
    with zipfile.ZipFile(source_file, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=7) as z:
        for p, relative in source_files(SOURCE):
            add_file(z, p, ('ZyntaxAI-patched-source/' + relative.as_posix()))
        for name in ['BUILDER_REVISION', '.github/workflows/build-portable.yml',
                     'scripts/resolve_upstream.py', 'scripts/apply_portable.py',
                     'scripts/package_release.py', 'scripts/validate_packages.py',
                     'scripts/verify_release.py', 'scripts/fix_shared_publisher.py', 'runtime/Launch-ZyntaxAI.cmd',
                     'runtime/ZyntaxAI-Manager.cmd', 'runtime/README-PORTABLE.txt',
                     'README.md']:
            add_file(z, ROOT / name, 'portable-builder/' + name)
        z.writestr('SOURCE-IDENTITY.txt', source_notice)
    print(f'Native ZIP: {portable_file} ({portable_file.stat().st_size:,} bytes)')
    print(f'GPL source ZIP: {source_file} ({source_file.stat().st_size:,} bytes)')


if __name__ == '__main__':
    try:
        package()
    except (RuntimeError, ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        sys.exit(f'ERROR packaging: {exc}')
