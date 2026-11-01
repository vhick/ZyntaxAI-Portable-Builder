# Validation record — 2026-11-01 (v1.5, system tray autostart)

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

## v1.3 autostart manager validation

- Manager menu includes 5 = enable, 6 = disable, 7 = status; existing choices retained.
- The integration targets only `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` / `ZyntaxAI-Native-Portable` and never uses admin, tasks, or services.
- It points at `Launch-ZyntaxAI.cmd`, not at `App\zyntax.exe`, so the launcher's portable data environment applies.
- Registry registration is opt-in, has replacement and removal confirmations, and is reversible.
- Static source checks and ZIP packaging tests performed locally. Actual Windows `reg add` / `reg query` / `reg delete` behavior and successful Windows login launch are **NOT VERIFIED** in this non-Windows test environment; confirm on a real Windows user account.
- Live GitHub Actions compilation/publishing for builder revision r4 is **NOT VERIFIED**. Earlier successful compilation evidence is from r2.

## v1.4 Tauri host LocalAppData fix (2026-10-31)

- Observed defect: v1.3 can create `%LOCALAPPDATA%\dev.theholyonez.zyntaxai` even though its CMD launcher sets `WEBVIEW2_USER_DATA_FOLDER`; Tauri's own default data-directory creation occurs before the Microsoft WebView2 override.
- Source evidence: stable upstream v1.0.2 contains two auto-created windows (`main`, `overlay`) and a `.setup` hook; Tauri 2.11.5 supports `WindowConfig.create=false`, `WebviewWindowBuilder::from_config`, and `data_directory(PathBuf)`.
- Revision r5 sets both `create=false` and creates both windows from their unchanged original configurations with explicit `Data\WebView2` storage. Does not edit the base framework or upgrade the lockfile.
- The manager adds choice 8 to inspect the existing residual LocalAppData directory; `rmdir` (no `/s`) can remove an empty directory after confirmation, never nonempty user data.
- These are static and simulated checks; no actual Windows compile or clean-host test of r5 has yet occurred.
- Existing folders from prior portable versions are not removed automatically. Third-party Windows caches and other OS bookkeeping are beyond this portability redirection.

- Added early environment validation before `logging::init()` after inspecting upstream `logging.rs` and `Paths::from_env()`. A direct EXE launch without ZYNTAX_DATA_DIR should no longer create settings/logs in the host profile.

## v1.5 tray-start autostart update (2026-11-01)

- Confirmed from official upstream v1.0.2 `src-tauri/src/lib.rs`: `ARG_MINIMIZED` is `--minimized`; on first startup this makes `start_hidden=true`, installs the tray, and hides Settings instead of showing it.
- The v1.4 portable launcher forwards `%*`, so the builder modifies only the HKCU Run command in `ZyntaxAI-Manager.cmd`: it now appends `--minimized` after the quoted portable launcher path.
- The existing manager still enables/disables/status-checks exactly one HKCU Run value, requires no elevation, and keeps every previous menu option. `7` also warns when an old entry lacks the argument.
- Tests cover the presence of `--minimized` in the startup command, the legacy-entry diagnostic, preserved launch-argument forwarding, original portability/patch fixtures, and repository YAML and ZIP integrity.
- This test environment is Linux; it cannot execute `reg.exe`, Windows login, or the ZyntaxAI GUI. **No actual Windows logon test performed.** No new compiled Rust changes are introduced; existing r5 executable may be reused.
- Antivirus friendliness: no PowerShell/VBS helpers, process hiding, process injection, new persistence mechanism, scheduled task, or administrative privilege. Standard readable CMD + reg.exe; AV false positives cannot be ruled out.
