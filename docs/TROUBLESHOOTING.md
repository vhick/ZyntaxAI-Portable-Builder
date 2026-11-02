# Native builder troubleshooting

- **No stable version tag:** This repository builds official numerical Git tags, not `main`. Confirm the upstream version is tagged. Do not switch automatically to unstable source.
- **Patch anchor mismatch:** Upstream has changed windows, secrets, updater or startup implementation. Inspect the new source and update the patch to match exactly; never ignore the mismatch.
- **Rust/Tauri compilation:** Check first compiler error. Tauri desktop builds must use `pnpm tauri build --ci --no-bundle` and require full MSVC build tools and WebView2 SDK dependencies. No code-signing key is expected for this unsigned portable build.
- **Windows credential manager entries:** The portable build forces file-backed credentials only when launched via the root portable EXE. Never open `App/ZyntaxAI/zyntax.exe` directly.
- **Tauri home directories remain:** Window-state plugin is intentionally removed, WebView2 is manually bound to Data, but newly added upstream plugins may introduce new paths. Use bounded TraceGuard host snapshots and process-attributed tracing; add path redirection before cleanup.
- **Cannot autostart after drive move:** Open `ZyntaxAI-Manager.cmd` and choose Install/Repair. It checks only the per-user `ZyntaxAIPortable` Run value.
- **Startup visible:** Check registry command contains `--minimized` and launches `ZyntaxAIPortable.exe`, not `zyntax.exe`. Use the manager's status display.
- **Missing Microsoft Edge WebView2:** Install Microsoft's supported runtime through its official installer; this is a Windows runtime dependency, not necessarily a portability defect.
- **Release already exists:** Do not use `gh release upload --clobber`. Increment builder revision after meaningful source changes; preserve manually curated releases.
- **Host data collision:** Do not delete an installed ZyntaxAI profile or overwrite credentials. Source-level portable paths are separate; TraceGuard remains a reporting monitor.
- **AV detection:** Submit the actual unsigned binary for independent analysis/signing; do not add exclusions, encoded PowerShell or auto-elevation to evade security products.

- **Visual Studio 17 2022 generator missing (r1 error):** GitHub `windows-latest` moved to Visual Studio 2026. r2 runs `scripts/build_launcher.ps1`, detects MSVC with `vswhere`, chooses VS 17/18 generator, and requires CMake >= 4.2 for VS 2026. The runner must include x64 MSVC tools. Do not switch to an unsupported or guessed generator.
