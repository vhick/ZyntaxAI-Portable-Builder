#!/usr/bin/env python3
"""Assemble, verify and checksum native portable ZIP and GPL source ZIP."""
import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def pe_details(path):
    data = pathlib.Path(path).read_bytes()
    if len(data) < 512 or data[:2] != b'MZ':
        raise ValueError(f'{path}: not a valid Windows PE binary')
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    if pe + 92 > len(data) or data[pe:pe+4] != b'PE\0\0':
        raise ValueError(f'{path}: missing PE header')
    machine = struct.unpack_from('<H', data, pe+4)[0]
    optional = pe + 24
    opt_magic = struct.unpack_from('<H', data, optional)[0]
    subsystem = struct.unpack_from('<H', data, optional+68)[0]
    if machine != 0x8664 or opt_magic != 0x20B:
        raise ValueError(f'{path}: expected x64 PE32+; machine={machine:x}, magic={opt_magic:x}')
    return {'machine': machine, 'subsystem': subsystem}


def zip_directory(directory, archive):
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=7, allowZip64=True) as z:
        for file in sorted(directory.rglob('*')):
            if file.is_file():
                z.write(file, file.relative_to(directory).as_posix())
    with zipfile.ZipFile(archive, 'r') as z:
        if z.testzip() is not None:
            raise RuntimeError(f'Corrupt ZIP member in {archive}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--launcher', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--revision', default='r2')
    args = parser.parse_args()
    upstream = pathlib.Path(args.upstream).resolve()
    launcher = pathlib.Path(args.launcher).resolve()
    exe = upstream / 'target/release/zyntax.exe'
    launch_pe = pe_details(launcher)
    app_pe = pe_details(exe)
    if launch_pe['subsystem'] != 2 or app_pe['subsystem'] != 2:
        raise ValueError('Expected GUI-subsystem Windows PE binaries, not console wrappers')
    if not (upstream / 'src-tauri/icons/icon.ico').exists():
        raise ValueError('Official upstream application icon missing')
    if not (upstream / 'LICENSE').exists():
        raise ValueError('Upstream GPL license file missing')
    if (upstream / 'src-tauri/src/lib.rs').read_text(encoding='utf8').count('ZYNTAX_PORTABLE_WEBVIEW_DIR') != 1:
        raise ValueError('Source-level WebView2 redirection is not present exactly once')
    sha = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    version_file = json.loads((upstream / 'src-tauri/tauri.conf.json').read_text(encoding='utf8'))
    if version_file['version'] != args.version:
        raise ValueError('Requested version differs from tagged upstream config')
    with tempfile.TemporaryDirectory(prefix='zyntaxpkg-') as tmp:
        work = pathlib.Path(tmp)
        package = work / 'ZyntaxAIPortable'
        app = package / 'App' / 'ZyntaxAI'
        app.mkdir(parents=True)
        (package / 'Data').mkdir()
        (package / 'Other').mkdir()
        shutil.copy2(launcher, package / 'ZyntaxAIPortable.exe')
        shutil.copy2(exe, app / 'zyntax.exe')
        shutil.copy2(upstream / 'LICENSE', package / 'Other' / 'LICENSE-GPL-3.0.txt')
        shutil.copy2(ROOT / 'manager/ZyntaxAI-Manager.cmd', package / 'ZyntaxAI-Manager.cmd')
        (package / 'Data' / 'README-KEEP-DATA.txt').write_text(
            'Never delete or replace the Data directory while upgrading.\n'
            'Settings, history, encryption key, encrypted API credentials, WebView2 and logs live here.\n',
            encoding='utf-8')
        (package / 'Other' / 'UPSTREAM-SOURCE.txt').write_text(
            f'Upstream: https://github.com/TheHolyOneZ/ZyntaxAI\n'
            f'Tag: {args.tag}\nCommit: {sha}\n'
            'Modified corresponding source and build scripts are in the separate -Source.zip asset.\n',
            encoding='utf-8')
        (package / 'Other' / 'PORTABILITY.txt').write_text(
            'Launch only ZyntaxAIPortable.exe.\n'
            'Autostart: open ZyntaxAI-Manager.cmd and select Install/Repair.\n'
            'Portable mode prevents direct use of Windows Credential Manager.\n'
            'TraceGuard monitors candidates but never deletes host data.\n'
            'This app requires the Microsoft Edge WebView2 runtime on Windows.\n',
            encoding='utf-8')
        buildinfo = {'upstream_tag': args.tag, 'upstream_version': args.version,
                     'upstream_commit': sha, 'builder_revision': args.revision,
                     'architecture': 'x64', 'mode': 'NATIVE', 'traceguard': 'report-only'}
        (package / 'Other' / 'BUILDINFO.json').write_text(json.dumps(buildinfo, indent=2) + '\n', encoding='utf8')
        dist = ROOT / 'dist'
        dist.mkdir(exist_ok=True)
        native_name = f'ZyntaxAIPortable_{args.version}_Native_x64_{args.revision}.zip'
        zip_directory(work, dist / native_name)
        with zipfile.ZipFile(dist / native_name) as archive:
            names = set(archive.namelist())
            for required in ['ZyntaxAIPortable/ZyntaxAIPortable.exe',
                             'ZyntaxAIPortable/App/ZyntaxAI/zyntax.exe',
                             'ZyntaxAIPortable/Data/README-KEEP-DATA.txt',
                             'ZyntaxAIPortable/ZyntaxAI-Manager.cmd']:
                if required not in names:
                    raise RuntimeError(f'Package verification failed: {required} missing')
        # The corresponding modified upstream source is an independent GPL source asset.
        source_root = work / 'Source'
        source_root.mkdir()
        files = subprocess.check_output(['git', '-C', str(upstream), 'ls-files', '-z'])
        for raw in files.split(b'\0'):
            if not raw: continue
            rel = pathlib.Path(raw.decode('utf8'))
            dest = source_root / 'Upstream-Modified' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(upstream / rel, dest)
        builder_dest = source_root / 'Portable-Builder'
        for rel in ['launcher/ZyntaxAIPortable.cpp', 'launcher/CMakeLists.txt', 'launcher/icon.rc',
                    'scripts/patch_upstream.py', 'scripts/build_launcher.ps1', 'scripts/package.py', 'scripts/validate_release.py',
                    'manager/ZyntaxAI-Manager.cmd',
                    '.github/workflows/build-native.yml', 'README.md', 'LICENSE-BUILDER-MIT.txt',
                    'tests/test_builder.py', 'tests/TraceGuard-HostSnapshot.ps1',
                    'docs/TROUBLESHOOTING.md']:
            dest = builder_dest / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest)
        (source_root / 'Upstream-Modified' / 'PORTABLE_PATCH_INFO.txt').write_text(
            f'Modified from tag {args.tag}, commit {sha}. GPL-3.0-or-later upstream.\n', encoding='utf-8')
        source_name = f'ZyntaxAIPortable_{args.version}_Source_{args.revision}.zip'
        # Only the Source/ directory is packaged into source asset.
        with zipfile.ZipFile(dist / source_name, 'w', zipfile.ZIP_DEFLATED, compresslevel=7) as z:
            for file in sorted(source_root.rglob('*')):
                if file.is_file(): z.write(file, file.relative_to(source_root.parent).as_posix())
        with zipfile.ZipFile(dist / source_name) as z:
            if z.testzip() is not None: raise RuntimeError('Corrupt source ZIP')
        checksum_lines = []
        for asset in sorted(dist.glob('*.zip')):
            checksum_lines.append(f'{hashlib.sha256(asset.read_bytes()).hexdigest()}  {asset.name}')
        (dist / 'SHA256SUMS.txt').write_text('\n'.join(checksum_lines) + '\n', encoding='ascii')
        (dist / 'release-notes.md').write_text(
            f'ZyntaxAI upstream {args.version} ({args.tag}, {sha}) built as native portable {args.revision}.\n\n'
            'Launch ZyntaxAIPortable.exe; enable minimized login startup from ZyntaxAI-Manager.cmd or the app System panel. '
            'Keep Data when updating. Modified corresponding source is provided. '
            'No PortableApps .paf.exe is generated in NATIVE mode.\n', encoding='utf8')
        print(json.dumps({'buildinfo': buildinfo, 'assets': [native_name, source_name, 'SHA256SUMS.txt'],
                          'launcher_pe': launch_pe, 'app_pe': app_pe}, indent=2))

if __name__ == '__main__':
    main()
