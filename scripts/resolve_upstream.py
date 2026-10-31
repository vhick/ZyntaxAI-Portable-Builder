#!/usr/bin/env python3
"""Resolve a stable official release, clone its tag, and skip identical published builds."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.work'
UPSTREAM = 'TheHolyOneZ/ZyntaxAI'
API = 'https://api.github.com'
BUILDER_FILES = [
    '.github/workflows/build-portable.yml',
    'scripts/resolve_upstream.py',
    'scripts/apply_portable.py',
    'scripts/package_release.py',
    'scripts/validate_packages.py',
    'scripts/verify_release.py',
    'scripts/fix_shared_publisher.py',
    'runtime/Launch-ZyntaxAI.cmd',
    'runtime/ZyntaxAI-Manager.cmd',
    'runtime/README-PORTABLE.txt',
]
PUBLISH_MARKER = '<!-- portable-release-publisher:managed:v2 -->'
TAG_PATTERN = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')


def request_api(route: str):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'ZyntaxAI-Independent-Portable-Builder', 'X-GitHub-Api-Version': '2022-11-28'}
    token = os.environ.get('GH_TOKEN', '')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(API + route, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f'GitHub API returned HTTP {exc.code} for {route}: {exc.read(250)!r}') from exc


def stable_release():
    records = []
    for page in range(1, 4):
        batch = request_api(f'/repos/{UPSTREAM}/releases?per_page=100&page={page}')
        if not isinstance(batch, list):
            raise RuntimeError('Cannot read official GitHub Releases; no fallback to unverified main branch')
        for record in batch:
            tag = record.get('tag_name', '')
            match = TAG_PATTERN.fullmatch(tag)
            if match and not record.get('draft') and not record.get('prerelease'):
                records.append((tuple(map(int, match.groups())), tag))
        if len(batch) < 100:
            break
    if not records:
        raise RuntimeError('No official stable semantic-version release found; refusing a main-branch fallback')
    (_, tag) = max(records, key=lambda entry: entry[0])
    return tag, tag.lstrip('v')


def builder_fingerprint():
    h = hashlib.sha256()
    for name in BUILDER_FILES:
        file = ROOT / name
        if not file.is_file():
            raise RuntimeError(f'Missing required builder file: {name}')
        h.update(name.encode('utf-8') + b'\0')
        h.update(file.read_bytes())
        h.update(b'\0')
    return h.hexdigest()[:12]


def git(*args):
    subprocess.run(['git', *args], check=True, cwd=ROOT)


def out(name, value):
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f'{name}={value}\n')
    print(f'{name}={value}', flush=True)


def expected_zip_names(meta):
    stem = f"{meta['version']}-{meta['revision']}-win64"
    return {
        f'ZyntaxAI-Native-Portable-{stem}.zip',
        f'ZyntaxAI-Portable-Source-{stem}.zip',
    }


def verify_existing(meta):
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if not repo:
        print('No caller repository supplied; release lookup skipped (local/simulated run)')
        return False
    existing = request_api(f"/repos/{repo}/releases/tags/{meta['tag']}")
    if existing is None:
        return False
    if existing.get('draft') or PUBLISH_MARKER not in existing.get('body', ''):
        raise RuntimeError('The release tag already exists but is draft/unmanaged. Refusing to overwrite')
    assets = existing.get('assets', [])
    names = {a.get('name') for a in assets}
    expected = expected_zip_names(meta) | {'SHA256SUMS.txt'}
    if names != expected or any(not a.get('size') for a in assets):
        raise RuntimeError(f'Existing release contains unexpected/missing assets: {names!r}; expected {expected!r}')
    print('Publisher-managed release already contains the expected assets; skipping redundant build')
    return True


def main():
    rev = (ROOT / 'BUILDER_REVISION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'r[1-9][0-9]*', rev):
        raise RuntimeError('BUILDER_REVISION must be r1, r2, r3, etc.')
    official_tag, version = stable_release()
    WORK.mkdir(exist_ok=True)
    target = WORK / 'upstream'
    if target.exists():
        raise RuntimeError('Unexpected existing .work/upstream; refusing to reuse a possibly stale checkout')
    git('clone', '--depth', '1', '--branch', official_tag, f'https://github.com/{UPSTREAM}.git', str(target))
    sha = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    upstream_version = json.loads((target / 'src-tauri/tauri.conf.json').read_text(encoding='utf-8'))['version']
    package_version = json.loads((target / 'package.json').read_text(encoding='utf-8'))['version']
    if upstream_version != version or package_version != version:
        raise RuntimeError(f'Version mismatch (tag={version}, tauri={upstream_version}, package={package_version})')
    fingerprint = builder_fingerprint()
    tag = f'portable-v{version}-u{sha[:10]}-{rev}-p{fingerprint}'
    meta = {'upstream': UPSTREAM, 'upstream_tag': official_tag, 'version': version,
            'upstream_commit': sha, 'revision': rev, 'builder_fingerprint': fingerprint,
            'tag': tag}
    meta['portable_zip'], meta['source_zip'] = sorted(expected_zip_names(meta))
    (WORK / 'build-meta.json').write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    for key in ['tag', 'version', 'revision', 'upstream_commit']:
        out(key, meta[key])
    out('skip', str(verify_existing(meta)).lower())
    print(f'Official stable upstream: {official_tag} @ {sha}; build signature {fingerprint}')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, KeyError, subprocess.CalledProcessError, urllib.error.URLError) as error:
        sys.exit(f'ERROR resolving upstream: {error}')
