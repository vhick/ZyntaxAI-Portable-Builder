# Validation record — 2026-10-31 (v1.1)

This records checks performed in a Linux-based preparation environment, NOT a live
Windows build or a successful GitHub Actions publication.

## Verified upstream and publisher evidence

- Verified the official ZyntaxAI GitHub release tag `v1.0.2`, Tauri v2 project,
  `ZYNTAX_DATA_DIR`, native encrypted-file secret backend, OS autostart plugin,
  installer updater plugin, and GPL-3.0-or-later license from the upstream source.
- Verified the publisher v1 composite action and its `files`, `tag`,
  `release-title`, `keep-releases`, `prune`, `dry-run` inputs and its checksum,
  draft publication, and release-identity safeguards from its source.
- Confirmed the official Tauri 2.12.0 release introduces `appDirectoriesOverride`;
  pinned Tauri 2.11.5 cannot be assumed to understand it. Removed that setting.
- WebView2 browser profile uses Microsoft's documented
  `WEBVIEW2_USER_DATA_FOLDER` launcher override.

## Error fixed in v1.1

Uploaded log demonstrates that source cloning and version resolution succeeded, but the portability patch failed because the official stable autostart commands have a blank line between them. Replaced the old combined matcher with two independently anchored matchers. Updated the fixture to reflect the blank line and prevent regression. This is not a substitute for a live Windows build.

## Tests run locally

- Python script compilation (`python -m compileall -q scripts tests`): passed.
- Workflow configuration parsed with PyYAML: passed (syntactic check only).
- 4 Python unit tests (`python -m unittest discover -s tests -v`): passed.
- ZIP generation and validation with fixture executable/source: passed;
  both ZIP CRCs, manifest entries, and MZ executable-header checks passed.
- Static check that the workflow contains no `actions/upload-artifact`, has
  manual trigger, scoped contents:write, and calls a single shared publisher: passed.

## Not yet proven

- Windows MSVC/Rust compile of the actual unmodified developer v1.0.2 source
  after targeted portability patches. This requires the first live GitHub Actions run.
- Running ZyntaxAI with WebView2 on Windows; recording the precise host profile
  and registry footprint on a clean Windows user profile.
- Real remote upload and SHA-256 verification on GitHub Releases.
- Antivirus heuristic outcome for the resulting unsigned EXE.

Do not report this builder as successfully producing a real Windows binary
until its GitHub Actions compile and publish steps succeed. If an upstream API
changes, the explicit-match patch will fail and must be updated.
