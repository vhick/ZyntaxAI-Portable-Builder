#!/usr/bin/env python3
"""Apply a narrowly scoped Windows newline fix to a checkout of shared publisher @v1.

This does not fork or reimplement the publisher, and never touches its repository.
Fails closed if the original audited line changes or if the fix is already applied.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ORIGINAL = 'checksum_path.write_text(sums, encoding="utf-8")'
REPLACEMENT = 'checksum_path.write_bytes(sums.encode("utf-8"))'


def patch(publisher_dir: Path) -> Path:
    action = publisher_dir / 'action.yml'
    target = publisher_dir / 'scripts' / 'publish.py'
    if not action.is_file() or not target.is_file():
        raise RuntimeError('Expected shared publisher action.yml and scripts/publish.py in checkout')
    action_text = action.read_text(encoding='utf-8')
    if 'using: composite' not in action_text or 'PUBLISH_FILES:' not in action_text:
        raise RuntimeError('Unexpected shared publisher action interface. Refusing to patch.')
    source = target.read_text(encoding='utf-8')
    if source.count(ORIGINAL) != 1 or REPLACEMENT in source:
        raise RuntimeError('Expected upstream @v1 checksum writer not found exactly once. Refusing an uncertain patch.')
    if 'def remote_assets_match(' not in source or 'def verify_new_draft(' not in source:
        raise RuntimeError('Shared publisher verification interface changed unexpectedly.')
    target.write_bytes(source.replace(ORIGINAL, REPLACEMENT, 1).encode('utf-8'))
    after = target.read_text(encoding='utf-8')
    if after.count(REPLACEMENT) != 1 or ORIGINAL in after:
        raise RuntimeError('Publisher compatibility patch did not verify')
    print('Shared publisher @v1 Windows checksum compatibility fix applied (binary UTF-8 LF, no CRLF translation).', flush=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('publisher_dir', type=Path, help='Path to checkout of shared publisher @v1')
    args = parser.parse_args()
    patch(args.publisher_dir)

if __name__ == '__main__':
    main()
