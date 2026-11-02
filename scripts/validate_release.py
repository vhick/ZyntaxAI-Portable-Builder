#!/usr/bin/env python3
"""Additional release gate for ZIP integrity, data preservation and checksums."""
import argparse
import hashlib
import pathlib
import shutil
import tempfile
import zipfile
from package import pe_details

def validate(dist, version, revision):
    archives = sorted(dist.glob('*.zip'))
    if len(archives) != 2:
        raise RuntimeError(f'Expected native + source ZIP, got {len(archives)}')
    name = f'ZyntaxAIPortable_{version}_Native_x64_{revision}.zip'
    src = f'ZyntaxAIPortable_{version}_Source_{revision}.zip'
    native, source = dist / name, dist / src
    expected = {}
    for line in (dist / 'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
        sha, filename = line.split('  ', 1)
        expected[filename] = sha
    if set(expected) != {name, src}:
        raise RuntimeError('Checksums do not cover exactly the requested release ZIPs')
    for archive in (native, source):
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected[archive.name]:
            raise RuntimeError(f'Checksum mismatch: {archive}')
        with zipfile.ZipFile(archive) as z:
            bad = z.testzip()
            if bad: raise RuntimeError(f'ZIP corrupt: {bad}')
    with tempfile.TemporaryDirectory() as t:
        target = pathlib.Path(t)
        with zipfile.ZipFile(native) as z: z.extractall(target)
        root = target / 'ZyntaxAIPortable'
        launcher = root / 'ZyntaxAIPortable.exe'
        app = root / 'App/ZyntaxAI/zyntax.exe'
        if pe_details(launcher)['subsystem'] != 2: raise RuntimeError('Portable EXE is not Windows GUI')
        if pe_details(app)['subsystem'] != 2: raise RuntimeError('Tauri app is not Windows GUI')
        (root / 'Data/MyPersistentHistory.db').write_bytes(b'DO-NOT-DELETE-USER-DATA')
        # Simulate upgrade by replacing only shipped files, while preserving entire Data.
        with zipfile.ZipFile(native) as z:
            for member in z.namelist():
                if not member.startswith('ZyntaxAIPortable/Data/') and not member.endswith('/'):
                    dest = target / member
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(z.read(member))
        if (root / 'Data/MyPersistentHistory.db').read_bytes() != b'DO-NOT-DELETE-USER-DATA':
            raise RuntimeError('Persistent data damaged during update test')
        # Relocate an existing package into a different directory name.
        moved = target / 'renamed-on-another-drive-simulation'
        shutil.move(str(root), str(moved))
        if not (moved / 'ZyntaxAIPortable.exe').is_file() or not (moved / 'Data/MyPersistentHistory.db').is_file():
            raise RuntimeError('Relocation-preservation simulation failed')
    with zipfile.ZipFile(source) as z:
        required = ['Source/Upstream-Modified/src-tauri/src/lib.rs',
                    'Source/Upstream-Modified/LICENSE',
                    'Source/Portable-Builder/launcher/ZyntaxAIPortable.cpp']
        for p in required:
            if p not in z.namelist(): raise RuntimeError(f'Corresponding source missing: {p}')
    print('PASS: PE GUI, archive integrity, SHA256, source, upgrade sentinel, relocation simulation')

if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--dist', type=pathlib.Path, required=True)
    a.add_argument('--version', required=True)
    a.add_argument('--revision', required=True)
    args = a.parse_args()
    validate(args.dist, args.version, args.revision)
