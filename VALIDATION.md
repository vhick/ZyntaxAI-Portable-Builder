# Validation record — 2026-10-31 (v1.2, Windows release-publisher fix)

## Evidence from user’s second Windows GitHub Actions run

- Official upstream ZyntaxAI `v1.0.2` cloned and patched successfully.
- `pnpm tauri build --no-bundle --ci` completed successfully, producing `target/release/zyntax.exe`.
- `ZyntaxAI-Native-Portable-1.0.2-r2-win64.zip` and `ZyntaxAI-Portable-Source-1.0.2-r2-win64.zip` passed SHA-256 and ZIP CRC validation.
- Shared publisher `vhick/portable-release-publisher@v1` created draft release `portable-v1.0.2-u6e1213095a-r2-p24d319aaf122` but then failed draft verification. It retained the draft; publication did NOT succeed.

## Root cause verified against published publisher v1 source

- The script creates the checksum string with `\n` and calculates its expected UTF-8 encoded byte count.
- `checksum_path.write_text(sums, encoding="utf-8")` on Windows writes text-mode newline sequences as CRLF, adding one extra byte per checksum line.
- The publisher subsequently compares actual GitHub asset sizes against the shorter LF-only in-memory size and rejects the draft. Exact HTTP responses from the draft are not included in the uploaded run, but this code path reliably explains the observed mismatch; the failure text can also cover checksum content differences.
- The correction is limited to replacing that one line with `checksum_path.write_bytes(sums.encode("utf-8"))`, which writes precisely the bytes the publisher verifies.
- This builder checks out the existing public publisher v1 into `.work/publisher` and applies this one-line patch LOCALLY on the ephemeral Actions runner. The shared publisher repository and tag are not modified. Its existing validation, SHA-256, draft-to-published workflow and duplicate protections are preserved.
- Revision r3 and changed builder fingerprint select a NEW release tag, leaving the failed r2 draft untouched. Do not auto-delete a failed draft or change immutable published releases.

## Local tests

- Python compilation: passed.
- PyYAML syntax parsing: passed.
- 6 unit tests including Windows CRLF regression: passed.
- Synthetic Windows-style checksum-size mismatch reproduced; corrected binary write bytes verified.
- Source and ZIP fixture packaging/validation: passed.
- Workflow static checks: one publisher step, second checkout only after package validation, no `actions/upload-artifact`, manual trigger, `contents: write` job scope, no release pruning.

## Remaining verification

- No actual Windows execution of the compiled application was performed here. The uploaded run verifies Windows COMPILATION only.
- Live GitHub Releases publishing with this v1.2 patch has not been run; verify the new r3 draft creation, upload, SHA-256 checks and publishing in the next Actions run.
- Windows clean-host data footprint and AV heuristics remain untested.
