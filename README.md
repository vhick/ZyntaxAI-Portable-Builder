# ZyntaxAI Native Portable Builder v1.5 (Tray Autostart)

**Independent, unsigned, Windows x64 native portable builder.** Upstream: https://github.com/TheHolyOneZ/ZyntaxAI. `WORKFLOW_MODE=NATIVE`. This repository is an unofficial builder, **not** the developer's repository, and does not need a fork. The ZIP kit does **not** contain an application binary: GitHub Actions compiles one from the latest official stable upstream release.

## v1.5 update — Windows login starts in the system tray (r6)

The upstream ZyntaxAI application **already supports `--minimized`**. In its Rust `lib.rs`, the `start_hidden` flag is set from that argument and `windows::hide_settings(&handle)` is called after the tray is installed. The portable `Launch-ZyntaxAI.cmd` already forwards all arguments to `App\zyntax.exe`. Therefore **no new Rust, Tauri, or WebView2 patch is necessary** for tray startup. Sources: [upstream lib.rs v1.0.2](https://github.com/TheHolyOneZ/ZyntaxAI/blob/v1.0.2/src-tauri/src/lib.rs), [upstream tray.rs](https://github.com/TheHolyOneZ/ZyntaxAI/blob/v1.0.2/src-tauri/src/tray.rs).

- Manager option **5** now registers the same current-user HKCU Run entry but invokes `Launch-ZyntaxAI.cmd --minimized`. This uses the application's native tray mode while keeping `ZYNTAX_DATA_DIR` and the WebView2 directory inside `Data`.
- Option **6** removes exactly that registration; option **7** displays the registered command and identifies whether it uses `--minimized` (older registrations may open the main window).
- If autostart was enabled using v1.4, select option **5** to *replace* the existing registration. No administrator access and no scheduled tasks are needed.
- **Normal manually launching** `Launch-ZyntaxAI.cmd` still opens the settings window. Left-click the system tray icon to open it after startup. A CMD window can briefly appear at login because the launcher is a conventional CMD script.
- **Existing working v1.4 portable users:** Replace only `ZyntaxAI-Manager.cmd` with `runtime/ZyntaxAI-Manager.cmd` from this kit, run it, and select **5** to refresh the existing autostart registration. **You do not need to rebuild ZyntaxAI or replace `App\zyntax.exe`.** To include this updated manager in a *newly published* portable ZIP, commit the full builder kit and run GitHub Actions. Builder revision **r6** gives that release a new tag.
- This avoids antivirus-sensitive methods such as hidden PowerShell, VBS wrappers, window-hiding tools, or third-party startup programs. It uses only the standard `reg.exe`, `cmd.exe`, and ZyntaxAI's documented source-level launch argument. Unsigned programs may still trigger Windows warnings.

**Limitation:** ZyntaxAI's single-instance handler opens Settings when a *second* instance is started while one is already running. The start-minimized behavior is reliable for a normal cold Windows login; manually rerunning an autostart command while the application is already open may bring Settings to the front. This baseline behavior is intentionally unchanged to avoid risking the confirmed working r5 app.

## v1.4 fix — prevent Tauri creating `%LOCALAPPDATA%\dev.theholyonez.zyntaxai`

The Windows folder reported after v1.3 is Tauri's default application-local WebView directory, not the app's `ZYNTAX_DATA_DIR` storage. Setting `WEBVIEW2_USER_DATA_FOLDER` only redirects Microsoft's WebView2 engine; the older Tauri 2.11.5 framework can still create its default app-local directory before WebView2 starts.

**Source-level fix:** During patching, set `create: false` on BOTH original `main` and `overlay` windows in `src-tauri/tauri.conf.json`. In `src-tauri/src/lib.rs`, manually create both original windows using the pinned Tauri version's `WebviewWindowBuilder::from_config(...)` and `.data_directory(<Data>\WebView2)`. All original window options (size, URLs, transparency, focus, overlay, taskbar) remain in their original config; no layout is reimplemented. The Rust code refuses to start without an absolute `ZYNTAX_DATA_DIR` **before the logging system initializes** rather than silently writing to the host. No unsupported `appDirectoriesOverride`, symlink, service, administrator permission, or registry redirection is needed.

The bundled manager retains choices 5–7 for autostart and adds **8 = Inspect leftover LocalAppData folder**. That option attempts to remove it **only if empty** and after confirmation. A nonempty directory is deliberately left untouched for user review. Close the tray application fully before cleanup; never delete your portable `Data` folder.

**The v1.4 LocalAppData source fix required a fresh GitHub Actions compilation**: replacing only the manager cannot fix that older compiled defect. Revision **r5** generated a distinct release tag. The user subsequently confirmed that v1.4 works and resolves the LocalAppData folder issue on their Windows machine.

## v1.3 update — optional Windows login autostart in the portable manager

The packaged `ZyntaxAI-Manager.cmd` now exposes **5 = Enable**, **6 = Disable** and **7 = Status** for **Windows login autostart**, while retaining every previous menu feature. It edits only `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` value `ZyntaxAI-Native-Portable` and never requests administrator privileges. The entry launches `Launch-ZyntaxAI.cmd` with the portable environment variables, **not** `App\zyntax.exe` directly. Status shows the registered command, and enabling an existing registration explicitly asks whether to replace it. Disabling requests confirmation and removes only that one value. No services, scheduled tasks or startup-folder copies are created. This system integration is **opt-in**, not installed at build time or automatically on first launch. A CMD window may briefly appear at login. If you move the portable folder, enable again to update the absolute path. Choose Disable before retiring the portable app; do not remove the `Data` folder when you upgrade.

The original upstream in-app autostart plugin remains disabled because it bypasses the portable launcher and could lose the environment-specific `Data` redirection. The in-app autostart toggle may therefore report that startup is disabled even when the **manager-owned** Windows registration exists. Use the manager's option 7 as the source of truth for the registry entry. Windows Startup Apps settings can independently disable a registered item.

For users with an already working v1.2 portable EXE, it is **not necessary to rebuild the application just to obtain these menu choices**: copy this builder kit's `runtime/ZyntaxAI-Manager.cmd` to the root of the existing extracted portable application, replacing its old manager. Keep `Launch-ZyntaxAI.cmd`, `App` and `Data` intact. Rebuilding using this complete kit is only needed if you want the v1.3 manager included in future published ZIP releases.

Builder revision for v1.3 was **r4**; v1.4 uses **r5**.

## v1.2 fix — shared release publisher rejects its own draft on Windows

**Verified live result from your second GitHub Actions run:** all build, package and ZIP verification stages passed. Rust/Tauri successfully compiled ZyntaxAI v1.0.2. The shared publisher created a draft but failed its own checksum verification. **No published release resulted.**

The shared publisher v1 source uses `checksum_path.write_text(sums, encoding="utf-8")`. On Windows, standard text-file writing converts LF to CRLF. However, the publisher calculates its expected checksum asset size using `len(sums.encode("utf-8"))` (LF-only). A checksum file for the two ZIPs is consequently **two bytes larger** than its expected size, causing the draft verification to fail.

**v1.2 fix:** This builder checks out the *original shared publisher* `vhick/portable-release-publisher` `v1` into the temporary `.work/publisher` directory. It applies a strictly checked one-line Windows compatibility patch to its script on the Actions runner: use `checksum_path.write_bytes(sums.encode("utf-8"))`. The entire existing publisher implementation (draft creation, SHA-256, duplicate protection, and release verification) stays intact. The publisher repository is not forked or modified. The action runs locally with `uses: ./.work/publisher` after checkout and patching, so there is still exactly ONE shared publisher responsible for releases. A future fix in the shared publisher repository should supersede this temporary compatibility shim.

Builder revision in the v1.2 fix was **r3**; the current v1.5 revision is **r6**. The previously failed **r2 draft is intentionally untouched**; there is no automatic draft deletion. You may inspect it through your GitHub Releases management interface while signed in, and remove it manually *only after verifying it is the failed incomplete draft*. It is not necessary to remove it to run v1.4.

**Upgrade using GitHub Desktop:** Extract this entire v1.5 ZIP over the local clone of your `ZyntaxAI-Portable-Builder` repo; replace earlier builder files but keep `.git`. Commit `Make ZyntaxAI Windows autostart open in tray (r6)` and Push origin. On GitHub.com → Actions → ZyntaxAI Native Portable - Build and Publish → Run workflow with `dry_run` unchecked. A successful run publishes both ZIPs plus `SHA256SUMS.txt` directly to Releases.

## What you get

After a successful GitHub Actions run, open **your builder repository → Releases**. Each successful release contains:

1. `ZyntaxAI-Native-Portable-VERSION-rN-win64.zip` — portable Windows executable, readable launchers and metadata; NO installer.
2. `ZyntaxAI-Portable-Source-VERSION-rN-win64.zip` — **complete corresponding GPL source** as compiled, with all portability patches and build scripts.
3. `SHA256SUMS.txt` — automatically created and uploaded by the `vhick/portable-release-publisher` v1 source checkout, with the one-line Windows checksum compatibility patch.

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

**Important framework compatibility:** ZyntaxAI v1.0.2 locks **Tauri 2.11.5**. Tauri introduced `app.appDirectoriesOverride` only in **2.12.0** (September 2026). This builder intentionally avoids adding that incompatible setting and instead uses Microsoft's documented, process-local WebView2 directory override. The host-profile window-state plugin is disabled, and the two original Tauri windows now use manual creation with explicit `Data\WebView2` storage. This addresses the observed Tauri-created empty LocalAppData folder; complete zero-trace behavior is **not verified**.

| Original behavior / relevant component | Portable behavior | Evidence in upstream source |
| --- | --- | --- |
| Rust `ProjectDirs::from("dev", "TheHolyOneZ", "ZyntaxAI")` resolves per-user config/data, typically under Windows roaming/local AppData. | Official `ZYNTAX_DATA_DIR` runtime setting points to `<portable-root>\Data`; no junctions needed. | `crates/zyntax-store/src/paths.rs` (`Paths::from_env`, `rooted_at`) |
| `settings.json` in OS config directory | `Data\config\settings.json` | `paths.rs`, `state.rs` |
| SQLite database / journal files in OS data directory | `Data\data\history.db`, including `-wal` and `-shm` while needed | `paths.rs`, `history.rs` |
| Rotating log files in OS data directory | `Data\data\logs\` | `src-tauri/src/logging.rs` |
| API keys through Windows Credential Manager, service `dev.theholyonez.zyntaxai`; fallback only when keychain unavailable | Portable code forces developer's existing `SecretStore::file_backed` AES-GCM store: `Data\data\secrets.key` and `Data\data\secrets.enc`. | `crates/zyntax-store/src/secrets.rs`, `src-tauri/src/state.rs` |
| Tauri/WebView2 browser profile normally defaults to OS profile; window-state plugin saves `.window-state.json` in OS application config | Launcher sets documented `WEBVIEW2_USER_DATA_FOLDER` to `Data\WebView2`. Disable window-state plugin and set `create: false` on both windows, then use `WebviewWindowBuilder::from_config(...).data_directory(<Data>\WebView2)` so Tauri does not create its default local profile. Existing older-build leftovers require manual review. | `src-tauri/src/lib.rs`, Windows WebView2 documentation; upstream Tauri 2.11 lockfile |
| Tauri Windows autostart plugin uses Windows user Run registration (typically `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`). | Disable the upstream in-app plugin so it cannot launch the EXE without the portable environment. The optional **manager-owned** HKCU Run value `ZyntaxAI-Native-Portable` invokes `Launch-ZyntaxAI.cmd`. Options 5/6 add/remove only this value; 7 shows it. | `src-tauri/src/lib.rs`, `commands.rs`, `runtime/ZyntaxAI-Manager.cmd` |
| Tauri updater downloads and installs officially signed installer-based updates | Do not register updater plugin. In-app update-check/install commands return a clear portable-edition message; startup checks disabled. | `src-tauri/src/updates.rs`, `commands.rs`, `lib.rs` |
| Windows global hotkey, clipboard access, notifications and WebView2 runtime | Keep normal supported Windows integrations without installing dedicated service, driver, or scheduled task. The OS WebView2 runtime remains a system dependency. | Tauri/plugin configuration, `crates/zyntax-platform/` |

**Privacy caution:** portable encrypted API secrets keep the encryption key next to encrypted data, so anyone who copies the entire `Data` folder can potentially decrypt stored credentials. This differs from storing secrets in Windows Credential Manager. Use drive-level encryption where appropriate. Keys saved by an *installed* ZyntaxAI instance in Credential Manager do **not** automatically move into the portable edition. Re-enter them.

**No zero-trace guarantee:** The v1.4 source patch should prevent Tauri from creating its default application-local WebView directory, but it has not yet been verified through a clean Windows launch; existing folders from previous builds remain until inspected. Windows may also maintain OS caches, notification state, global shortcut registrations (while running), temporary files, Defender/SmartScreen metadata, execution histories, and WebView2 runtime infrastructure. These are not application-specific writable files we can safely eliminate. The plain launcher makes no permanent registry changes. **Only if you choose manager option 5** does it create one reversible HKCU startup value; option 6 removes it.

### Layout of the produced portable ZIP

```text
ZyntaxAI Native Portable/
  Launch-ZyntaxAI.cmd             <- Recommended start method
  ZyntaxAI-Manager.cmd            <- Interactive console with autostart and legacy-folder inspection
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

Running `App\zyntax.exe` directly bypasses `ZYNTAX_DATA_DIR` and must be avoided. In v1.4 and later, the compiled application checks for an absolute `ZYNTAX_DATA_DIR` **before initializing its logger** and exits if missing; use the launcher. The launcher never adds permanent environment variables.

**Manager commands:** Open `ZyntaxAI-Manager.cmd`, select **5** to register Windows tray autostart (`--minimized`), **6** to remove it, **7** to inspect its current registration, or **8** to inspect the old LocalAppData folder (remove only if empty). The registry location is `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value `ZyntaxAI-Native-Portable`. This is only for the current signed-in user and does **not** start a Windows service or run before login. If the portable folder is moved, select 5 again. Before deleting the portable folder, select 6. The app's own in-app "Start with Windows" toggle remains intentionally unavailable; the manager owns this optional feature.


## GitHub Desktop: first-time setup

1. Open **https://github.com/new** in your browser. Enter a name such as `ZyntaxAI-Portable-Builder`; leave **Initialize this repository with a README** unchecked (optional, but avoids initial conflicts).
2. Choose **Public** or **Private**. This controls whether your portable releases will be public or private. **You** choose; this kit never changes visibility. Click **Create repository**.
3. On the empty GitHub repository page, choose **Set up in Desktop** (or copy the repository URL). Open **GitHub Desktop → File → Clone repository → URL**, paste your builder repo URL, and choose your local folder.
4. Extract the downloadable **builder kit ZIP** directly into that cloned folder. After extraction, the folder must contain `.github`, `scripts`, `runtime`, `tests`, `README.md`, and `BUILDER_REVISION`. **Do not create or copy a `.git` folder.** The ZIP doesn't contain one; GitHub Desktop owns it.
5. In GitHub Desktop, verify the changed files. Enter a commit summary such as `Add ZyntaxAI native portable builder` and click **Commit to main**, then **Push origin** (or **Publish repository** if you created the project locally).
6. On GitHub.com, open your builder repository → **Settings → Actions → General**. Permit GitHub Actions and the required reusable actions. If policy restricts third-party repositories, allow the official GitHub `actions/checkout` action and checkout of `vhick/portable-release-publisher` v1. The build job explicitly requests `contents: write`; depending on repo-level policy, you may also need to allow workflows with write permissions.
7. Open **Actions → ZyntaxAI Native Portable - Build and Publish → Run workflow**. Keep `dry_run` unchecked to publish, or enable it for a first validation-only build.
8. Select **Run workflow**. Open the run to inspect each step. It is normal for the first Rust/Node compilation to take longer; the workflow timeout is 120 minutes.
9. Once completed successfully, open the builder repository's **Releases** page (not `Actions → Artifacts`). Download `ZyntaxAI-Native-Portable-...zip`. The same release includes the patched corresponding-source ZIP and `SHA256SUMS.txt`.
10. In a future update, click **Run workflow** again. The workflow checks official stable releases on every run and skips known identical publisher-managed releases. When you intentionally modify portability or packaging scripts, increment `BUILDER_REVISION` to the next revision (currently `r6`) in GitHub Desktop, commit and push.

There is **no upstream fork** and no manual ZIP upload. The producer's source remains unchanged upstream; all patches are applied to a temporary checkout on the GitHub runner.

### Direct GitHub Releases publisher

Verified reference: `vhick/portable-release-publisher` v1, a reusable composite GitHub Action accepting `files`, `tag`, `release-title`, `keep-releases`, `prune`, `dry-run` (and `tag-prefix`). The v1 tag was confirmed via the official `raw.githubusercontent.com/.../v1/action.yml` file. The shared repository remains unchanged; this is a runner-local compatibility correction. Its publisher script checks ZIPs, creates SHA256 sums, uploads a **draft** release directly, verifies asset hashes, then makes it public to people who can see that repository. It refuses inconsistent existing releases and avoids touching unrelated manual releases.

- **Action version:** the workflow checks out the public publisher at tag `v1`, applies the one-line Windows checksum patch on the disposable runner, then invokes `uses: ./.work/publisher`. It cannot use unpatched `@v1` on Windows until that publisher fixes the CRLF mismatch. For production, pin the `ref:` to the verified full commit SHA using `git ls-remote https://github.com/vhick/portable-release-publisher.git refs/tags/v1`; do not invent one.
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

The scripts are plain Python and CMD, with readable commands. No encoded PowerShell, disabled antivirus, UAC prompts, stealth scheduled tasks, registry hijacking, or permanent environment edits. The manager uses a single documented HKCU Run entry only at the user's request; it can be removed with option 6. The resulting EXE is unsigned unless you provide existing legitimate signing infrastructure separately; AV/SmartScreen warnings may still occur. The publisher action operates without AV exclusions.

## Local validation and troubleshooting

- **Autostart registration missing:** Use manager option 7 and check the displayed Windows Run command. If the application was moved, use option 5 to replace the old path. Confirm Windows Settings > Apps > Startup has not disabled ZyntaxAI.
- **Autostart works but settings are missing:** The startup entry must call `Launch-ZyntaxAI.cmd`, not `App\zyntax.exe`; use option 5 to repair it.
- **Autostart removal before uninstall:** Use option 6 before removing the portable directory. Only the named `ZyntaxAI-Native-Portable` Run value is removed; there are no services or scheduled tasks to clean up.


`python -m unittest discover -s tests -v` (also run automatically before source retrieval in GitHub Actions) tests the builder's patch logic against upstream-layout fixtures, packaging and ZIP checks. The CI run additionally verifies the actual upstream checkout, Rust/TypeScript compile, ZIP integrity, and publisher delivery.

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

## Validation status as of 2026-11-01 (v1.5)

- Source audit of the official tagged v1.0.2 code: **performed via live upstream raw files**.
- Shared publisher @v1 interface and its release-protection logic: **inspected via live upstream raw files**.
- Builder Python compilation, workflow YAML parsing, package-content verification, controlled source-patch tests, and ZIP fixture simulation: **performed locally** (see `VALIDATION.md`).
- Live Windows Rust/Tauri compilation and ZIP packaging: **CONFIRMED for an earlier revision by the uploaded v1.1 GitHub Actions log**. The user subsequently confirmed v1.4 r5 builds and runs successfully on their Windows system.
- Windows app execution, clean-host footprint and successfully published GitHub release with this v1.4 patch and v1.2 checksum fix: **CONFIRMED BY USER for v1.4 r5; v1.5 manager tray-mode changes have not been verified by a Windows sign-in.**

**v1.5 regression note:** Confirm Windows sign-in after enabling manager option 5. The startup command must include `--minimized`, which the original upstream application supports. The application should remain in the tray, not remain minimized in the taskbar.
