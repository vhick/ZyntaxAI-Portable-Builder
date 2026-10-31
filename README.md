# ZyntaxAI Native Portable Builder v1.0

**Independent, unsigned, Windows x64 native portable builder.** Upstream: https://github.com/TheHolyOneZ/ZyntaxAI. `WORKFLOW_MODE=NATIVE`. This repository is an unofficial builder, **not** the developer's repository, and does not need a fork. The ZIP kit does **not** contain an application binary: GitHub Actions compiles one from the latest official stable upstream release.

## What you get

After a successful GitHub Actions run, open **your builder repository → Releases**. Each successful release contains:

1. `ZyntaxAI-Native-Portable-VERSION-rN-win64.zip` — portable Windows executable, readable launchers and metadata; NO installer.
2. `ZyntaxAI-Portable-Source-VERSION-rN-win64.zip` — **complete corresponding GPL source** as compiled, with all portability patches and build scripts.
3. `SHA256SUMS.txt` — automatically created and uploaded by `vhick/portable-release-publisher@v1`.

The builder has a manual trigger only. No schedules or push triggers, no `actions/upload-artifact`, no Git LFS, and no deployment to a second repository. The shared publisher owns the **only** release creation/upload step.

## Source verification and build

- Fetch the GitHub Releases API for `TheHolyOneZ/ZyntaxAI`, select the highest stable numeric release tag (`vMAJOR.MINOR.PATCH`), ignore drafts/prereleases/alpha/beta/nightly. **Fail** if no stable release exists: no silent main-branch fallback.
- `git clone --depth 1 --branch <stable-tag>` directly from the official upstream repository; record the exact SHA in `.work/build-meta.json` and the finished ZIP.
- Assert package and Tauri versions match selected tag, then apply exact-match portability patches. Unexpected upstream source changes **fail the build** instead of producing a questionable portable.
- `pnpm install --frozen-lockfile` from upstream `pnpm-lock.yaml`; compile using **`pnpm tauri build --no-bundle --ci`**, which embeds the frontend using Tauri's `custom-protocol` feature. Never use plain `cargo build --release` here.
- Use official Node.js 22, pnpm 10.33.0, and Rust stable/MSVC on the standard `windows-2022` hosted runner. Tauri project requires Rust >=1.85.
- Package `target/release/zyntax.exe` (not NSIS/MSI installers) as `App/zyntax.exe`; validate Windows `MZ` header, ZIP CRC, expected members, and file size before handing it to the publisher.

**Upstream release inspected for this kit:** `v1.0.2` (`6e12130...` shown on the official release page). The workflow always resolves again at run time. If a future upstream stable version changes internal Rust paths or command interfaces, adjust the transparent patch script and increment `BUILDER_REVISION`, then rebuild.

## Storage audit — paths and fixes

**Important framework compatibility:** ZyntaxAI v1.0.2 locks **Tauri 2.11.5**. Tauri introduced `app.appDirectoriesOverride` only in **2.12.0** (September 2026). This builder intentionally avoids adding that incompatible setting and instead uses Microsoft's documented, process-local WebView2 directory override. The host-profile window-state plugin is disabled. This preserves critical user data while leaving the small potential for a Tauri-created empty AppData directory; a fully zero-trace build is **not verified**.

| Original behavior / relevant component | Portable behavior | Evidence in upstream source |
| --- | --- | --- |
| Rust `ProjectDirs::from("dev", "TheHolyOneZ", "ZyntaxAI")` resolves per-user config/data, typically under Windows roaming/local AppData. | Official `ZYNTAX_DATA_DIR` runtime setting points to `<portable-root>\Data`; no junctions needed. | `crates/zyntax-store/src/paths.rs` (`Paths::from_env`, `rooted_at`) |
| `settings.json` in OS config directory | `Data\config\settings.json` | `paths.rs`, `state.rs` |
| SQLite database / journal files in OS data directory | `Data\data\history.db`, including `-wal` and `-shm` while needed | `paths.rs`, `history.rs` |
| Rotating log files in OS data directory | `Data\data\logs\` | `src-tauri/src/logging.rs` |
| API keys through Windows Credential Manager, service `dev.theholyonez.zyntaxai`; fallback only when keychain unavailable | Portable code forces developer's existing `SecretStore::file_backed` AES-GCM store: `Data\data\secrets.key` and `Data\data\secrets.enc`. | `crates/zyntax-store/src/secrets.rs`, `src-tauri/src/state.rs` |
| Tauri/WebView2 browser profile normally defaults to OS profile; window-state plugin saves `.window-state.json` in OS application config | Launcher sets documented `WEBVIEW2_USER_DATA_FOLDER` to `Data\WebView2`. Disable window-state plugin to prevent its host AppData writes. **Tauri 2.11 may still create an empty application-local folder in the host profile.** | `src-tauri/src/lib.rs`, Windows WebView2 documentation; upstream Tauri 2.11 lockfile |
| Tauri Windows autostart plugin uses Windows user Run registration (typically `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`). | Do not register plugin; `set_autostart` returns a clear error and `is_autostart_enabled` returns false. | `src-tauri/src/lib.rs`, `commands.rs`, `src-tauri/Cargo.toml` |
| Tauri updater downloads and installs officially signed installer-based updates | Do not register updater plugin. In-app update-check/install commands return a clear portable-edition message; startup checks disabled. | `src-tauri/src/updates.rs`, `commands.rs`, `lib.rs` |
| Windows global hotkey, clipboard access, notifications and WebView2 runtime | Keep normal supported Windows integrations without installing dedicated service, driver, or scheduled task. The OS WebView2 runtime remains a system dependency. | Tauri/plugin configuration, `crates/zyntax-platform/` |

**Privacy caution:** portable encrypted API secrets keep the encryption key next to encrypted data, so anyone who copies the entire `Data` folder can potentially decrypt stored credentials. This differs from storing secrets in Windows Credential Manager. Use drive-level encryption where appropriate. Keys saved by an *installed* ZyntaxAI instance in Credential Manager do **not** automatically move into the portable edition. Re-enter them.

**No zero-trace guarantee:** Tauri 2.11 may create an otherwise empty application-local directory in `%LOCALAPPDATA%` even with WebView2 cache redirected. Windows may also maintain OS caches, notification state, global shortcut registrations (while running), temporary files, Defender/SmartScreen metadata, execution histories, and WebView2 runtime infrastructure. These are not application-specific writable files we can safely eliminate. No administrator privilege or permanent registry change is required by this builder's launcher.

### Layout of the produced portable ZIP

```text
ZyntaxAI Native Portable/
  Launch-ZyntaxAI.cmd             <- Recommended start method
  ZyntaxAI-Manager.cmd            <- Small interactive console
  README-PORTABLE.txt
  LICENSE.txt
  SOURCE-CODE.txt
  RELEASE-METADATA.json
  App/
    zyntax.exe                    <- Unsigned, compiled Windows EXE
  Data/                           <- PRESERVE ACROSS UPDATES
    .keep                         <- Placeholder only
    config/settings.json          <- Created on first run
    data/history.db               <- Created on first run
    data/secrets.enc              <- Created when key is saved
    data/secrets.key              <- KEEP WITH secrets.enc
    data/logs/                    <- Created on first run
    WebView2/                     <- Browser cache and local browser storage
```

### Update an existing portable installation

1. Fully quit ZyntaxAI from its tray menu (closing the settings window might only minimize it).
2. Extract a **new release ZIP to a different new folder**.
3. Move or copy your existing entire `Data` directory into that new folder. If Windows asks about merging, first remove the new folder's placeholder-only `Data` directory, then move your old `Data` as a whole.
4. Double-click the new `Launch-ZyntaxAI.cmd`. Verify settings, usage records, and API-key availability.
5. Keep your old copy as backup until verified. **Never copy a freshly uninitialized `Data` folder over existing real data.**

Running `App\zyntax.exe` directly bypasses `ZYNTAX_DATA_DIR` and must be avoided. The WebView2 directory override is passed only by the CMD launcher, and the app's own Rust settings/history would revert to the OS profile. The launcher never adds permanent environment variables.

## GitHub Desktop: first-time setup

1. Open **https://github.com/new** in your browser. Enter a name such as `ZyntaxAI-Portable-Builder`; leave **Initialize this repository with a README** unchecked (optional, but avoids initial conflicts).
2. Choose **Public** or **Private**. This controls whether your portable releases will be public or private. **You** choose; this kit never changes visibility. Click **Create repository**.
3. On the empty GitHub repository page, choose **Set up in Desktop** (or copy the repository URL). Open **GitHub Desktop → File → Clone repository → URL**, paste your builder repo URL, and choose your local folder.
4. Extract the downloadable **builder kit ZIP** directly into that cloned folder. After extraction, the folder must contain `.github`, `scripts`, `runtime`, `tests`, `README.md`, and `BUILDER_REVISION`. **Do not create or copy a `.git` folder.** The ZIP doesn't contain one; GitHub Desktop owns it.
5. In GitHub Desktop, verify the changed files. Enter a commit summary such as `Add ZyntaxAI native portable builder` and click **Commit to main**, then **Push origin** (or **Publish repository** if you created the project locally).
6. On GitHub.com, open your builder repository → **Settings → Actions → General**. Permit GitHub Actions and the required reusable actions. If policy restricts third-party actions, permit `vhick/portable-release-publisher@v1`. The build job explicitly requests `contents: write`; depending on repo-level policy, you may also need to allow workflows with write permissions.
7. Open **Actions → ZyntaxAI Native Portable - Build and Publish → Run workflow**. Keep `dry_run` unchecked to publish, or enable it for a first validation-only build.
8. Select **Run workflow**. Open the run to inspect each step. It is normal for the first Rust/Node compilation to take longer; the workflow timeout is 120 minutes.
9. Once completed successfully, open the builder repository's **Releases** page (not `Actions → Artifacts`). Download `ZyntaxAI-Native-Portable-...zip`. The same release includes the patched corresponding-source ZIP and `SHA256SUMS.txt`.
10. In a future update, click **Run workflow** again. The workflow checks official stable releases on every run and skips known identical publisher-managed releases. When you intentionally modify portability or packaging scripts, increment `BUILDER_REVISION` from `r1` to `r2` in GitHub Desktop, commit and push.

There is **no upstream fork** and no manual ZIP upload. The producer's source remains unchanged upstream; all patches are applied to a temporary checkout on the GitHub runner.

### Direct GitHub Releases publisher

Verified reference: `vhick/portable-release-publisher@v1`, a reusable composite GitHub Action accepting `files`, `tag`, `release-title`, `keep-releases`, `prune`, `dry-run` (and `tag-prefix`). The v1 tag was confirmed via the official `raw.githubusercontent.com/.../v1/action.yml` file. Its publisher script checks ZIPs, creates SHA256 sums, uploads a **draft** release directly, verifies asset hashes, then makes it public to people who can see that repository. It refuses inconsistent existing releases and avoids touching unrelated manual releases.

- **Action version:** `@v1` verified and usable. This kit does not claim a full commit-SHA pin, because a trusted exact SHA could not be independently retrieved in the audit environment. For stronger future supply-chain pinning, obtain the full SHA with `git ls-remote https://github.com/vhick/portable-release-publisher.git refs/tags/v1` and replace `@v1` with that verified commit hash; do not invent a SHA.
- **Assets:** `files: dist/*.zip` intentionally includes the finished Windows binary ZIP **and** the complete GPL source ZIP; it cannot accidentally point to the upstream download archive.
- **Tags:** `portable-vVERSION-uUPSTREAMSHA10-rN-pBUILDERHASH12` includes upstream version, exact commit prefix, explicit builder revision and an automatic fingerprint of build scripts. Non-code README edits don't trigger new releases. Increment revision whenever actual packaging/patching behavior changes; the fingerprint additionally prevents silent tag collisions.
- **Existing releases:** a fast preflight checks for previously published matching managed release assets; it skips expensive compilation when the exact version/build fingerprint was published. On unexpected existing assets/draft/unmanaged release, it stops safely rather than overwriting.
- **Retention:** `keep-releases: 3`; `prune: false` (retention *limit* is configured but deletion is intentionally disabled). The script never deletes manually created releases. Opt into pruning only after separate explicit testing.
- **Credentials:** only the resolver and final release publisher/verification steps get `GITHUB_TOKEN`. `contents: write` is scoped to this single build job and GitHub's automatic repository token. No personal access token or additional secret is required.
- **Visibility:** GitHub Releases take on the builder repository's Public/Private visibility automatically; no cross-repository publish target.

The upstream GitHub Actions release workflow is not invoked. Its signed installers are not republished, and it cannot accidentally publish to your builder repo.

## GitHub Free protections and limitations

- Manual builds only; no timer or scheduled checks. Skip same stable source and same builder code/revision before Rust compilation.
- Single standard Windows hosted runner, max 120 minutes, one build at a time (`concurrency` group), no paid larger runner.
- ZIPs published directly within the same job through the publisher; **no Actions artifact storage**. Builds still consume GitHub Actions minutes (including private-repository quotas) and source/compiled files consume ephemeral runner disk; GitHub Releases assets consume GitHub release storage subject to provider policies. No unlimited-use claim.
- No dependency cache by default. This avoids accidental cache growth/storage and keeps the setup straightforward, at the cost of longer first/each-run dependency downloads.
- GitHub currently limits a single GitHub Release asset to **less than 2 GiB** as enforced by the shared publisher. Large Windows Rust builds may approach limits; the output must be inspected and trimmed in a legitimate manner if necessary.
- If GitHub API or dependency registries fail, the run reports an error. The publishing step executes **only after successful compilation, ZIP packaging and integrity verification**.

## Security and redistribution

The upstream project is **GPL-3.0-or-later**. Public redistribution of modified binaries carries source-code obligations: **both binary and full corresponding source archives** are published side by side, with licenses included, and the exact source SHA/build scripts retained. Keep the source ZIP with the binary release when sharing it.

Building source obtained from third parties runs their build scripts in the same Windows job as the later GitHub Release publishing operation. This is a conscious security tradeoff to avoid Actions artifact storage and duplicate jobs. Only enable this workflow for upstream code you trust. To isolate untrusted code properly, use separate restricted build and release jobs, requiring an artifact hand-off or other secure transfer; that would no longer meet the strict zero-Action-artifact approach. Avoid running this builder from untrusted pull requests. GitHub-hosted Windows runners are ephemeral, but this does not make third-party code inherently safe.

The scripts are plain Python and CMD, with readable commands. No encoded PowerShell, disabled antivirus, UAC prompts, stealth scheduled tasks, registry hijacking, or permanent environment edits. The resulting EXE is unsigned unless you provide existing legitimate signing infrastructure separately; AV/SmartScreen warnings may still occur. The publisher action operates without AV exclusions.

## Local validation and troubleshooting

`python -m unittest discover -s tests -v` tests the builder's patch logic against upstream-layout fixtures, packaging and ZIP checks. The CI run additionally verifies the actual upstream checkout, Rust/TypeScript compile, ZIP integrity, and publisher delivery.

**If the build fails:**

- **Missing upstream stable release:** the resolver deliberately stops. Check upstream official Releases. Do not change it to `main` without reviewing the security/maintenance implications.
- **Portability patch mismatch:** upstream Rust source structure changed. Inspect `src-tauri/src/{lib,state,commands}.rs` and `scripts/apply_portable.py` side by side. Update the exact targeted patch, run tests and bump `BUILDER_REVISION`.
- **pnpm frozen-lockfile failure:** official upstream package manifest and `pnpm-lock.yaml` conflict. Do not silently ignore the lockfile; investigate upstream integrity.
- **Rust/MSVC compile failure:** inspect `Build actual Windows application` logs. The official app may introduce new system dependencies. Keep building with Tauri CLI `--no-bundle`.
- **Missing EXE:** `package_release.py` expects `target/release/zyntax.exe` or `src-tauri/target/release/zyntax.exe`. If upstream changes binary name, update the package script with a verified new name and increment the builder revision.
- **403 on Releases:** check GitHub repository Actions permissions and `contents: write`; Actions may be restricted by organization policy. Do not create additional PATs before reviewing policy.
- **GitHub Release already exists:** if different, the publisher refuses to overwrite it. Increase builder revision after investigating; do not delete a protected or manually created release automatically.
- **WebView2 missing on target PC:** install the official Microsoft Edge WebView2 Runtime using Microsoft-provided methods, then restart ZyntaxAI. Do not bundle a questionable third-party WebView2 executable.
- **Old API keys missing:** installed-version keys live in Credential Manager and are not copied. Re-enter API keys through the portable UI.
- **Nothing appears after launch:** check `Data\data\logs`; ensure you used `Launch-ZyntaxAI.cmd`, the storage drive is writable, and no installed ZyntaxAI instance is already holding the single-instance lock.
- **Corrupt database after crash:** restore a backup of `Data` after completely exiting the app. Avoid copying `history.db` while it is in use; SQLite may have active `-wal` and `-shm` sidecar files.

## Validation status as of 2026-10-31

- Source audit of the official tagged v1.0.2 code: **performed via live upstream raw files**.
- Shared publisher @v1 interface and its release-protection logic: **inspected via live upstream raw files**.
- Builder Python compilation, workflow YAML parsing, package-content verification, controlled source-patch tests, and ZIP fixture simulation: **performed locally** (see `VALIDATION.md`).
- Live Windows Rust/Tauri build, WebView2 execution, and remote release upload: **NOT performed in this analysis environment**. A successful GitHub Actions run is required to verify them. Do not treat static test results as evidence of a successful released executable.
