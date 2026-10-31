#!/usr/bin/env python3
"""Post-publisher verification: ensure published (not draft) managed release + 3 assets."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

from resolve_upstream import request_api, PUBLISH_MARKER


def verify():
    meta = json.loads((Path(__file__).resolve().parents[1] / '.work/build-meta.json').read_text(encoding='utf-8'))
    repo = os.environ['GITHUB_REPOSITORY']
    record = request_api(f"/repos/{repo}/releases/tags/{meta['tag']}")
    if record is None or record.get('draft') or PUBLISH_MARKER not in record.get('body', ''):
        raise RuntimeError('Publisher did not leave a published, managed release at the expected tag')
    required = {meta['portable_zip'], meta['source_zip'], 'SHA256SUMS.txt'}
    assets = record.get('assets', [])
    names = {asset.get('name') for asset in assets}
    if names != required or any(not asset.get('size') for asset in assets):
        raise RuntimeError(f'Release assets do not match expected {required!r}: {names!r}')
    if record.get('immutable') and not record.get('assets'):
        raise RuntimeError('Immutable release is missing assets')
    print(f"Verified published release: {record.get('html_url')}")
    for asset in assets:
        print(f"  {asset['name']}: {asset['size']:,} bytes")


if __name__ == '__main__':
    try:
        verify()
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        sys.exit(f'ERROR verifying remote release: {error}')
