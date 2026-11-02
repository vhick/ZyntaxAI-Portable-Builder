# ZyntaxAI NATIVE Portable Builder r2

Independent, headless GitHub Actions builder for the official [TheHolyOneZ/ZyntaxAI](https://github.com/TheHolyOneZ/ZyntaxAI) Rust/Tauri 2 application. This is NOT a fork of the upstream repository, a PortableApps.com-certified package, or an MSI repack. **Selected mode: NATIVE, Windows x64 only.**

## What this ZIP builder kit produces

- `ZyntaxAIPortable_<upstream-version>_Native_x64_r2.zip` — full `ZyntaxAIPortable/` folder with a conventionally compiled, GUI-subsystem root `ZyntaxAIPortable.exe`, `App/ZyntaxAI/zyntax.exe`, `Data/`, runtime manager console and licensing.
- `ZyntaxAIPortable_<upstream-version>_Source_r2.zip` — the **modified corresponding GPL source**, launcher and all relevant reproducible builder scripts, to accompany binary redistribution.
- `SHA256SUMS.txt` — SHA-256 digests of both ZIPs.

**No `.paf.exe`** is produced because the requested mode is NATIVE, not PORTABLEAPPS or BOTH. No shared release publisher is needed. No schedule, unrequested registry change or service is created by the builder.

## Build and portability design

1. Query the upstream GitHub tags API. Select the greatest stable numeric `vMAJOR.MINOR.PATCH` (or `MAJOR.MINOR.PATCH`) tag; do NOT use prerelease tags or quietly compile `main`. Check out the tag by Git, record the exact SHA, and fail if its Tauri configuration version disagrees.
2. Patch the **temporary upstream checkout on the Windows runner**, leaving the original upstream repository untouched. Patch anchors are exact; changed structure fails the build instead of silently skipping portability changes.
3. ZyntaxAI's own documented `ZYNTAX_DATA_DIR` routes its config, SQLite history, file-encrypted API key and logs to `Data/ZyntaxAI`. The application is forced to use `SecretStore::file_backed` in portable mode so Windows Credential Manager is not used.
4. Tauri `main` and `overlay` windows are manually created with `WebviewWindowBuilder::data_directory(Data/WebView2)` and the window-state plugin is removed for this portable flavor to prevent its default app-config-directory writes. Main starts hidden until the app explicitly shows it. These changes are in modified source, not cleanup scripts.
5. The upstream in-app updater cannot install over the portable copy (`can_install_in_place=false`); use builder-generated releases for upgrades. Upstream's signed update **check** may still show an available update.
6. The patched System autostart switch and compiled launcher management options use the current root **portable** launcher in the per-user Windows Run key, with `--minimized`. The bundled `ZyntaxAI-Manager.cmd` offers Install/Repair, Remove, Status, Run normally, Run minimized and Self Test by calling built-in native launcher options (no PowerShell required). Autostart is opt-in, not silently installed by unzipping the app.
7. The compiled C++ root launcher locates the app and Data relative to **its own folder** and launches the bundled Tauri GUI binary with the data environment variables. The launcher stays active until the application process closes. No console is displayed by the normal GUI EXE. No administrator permissions are needed for normal use.
8. Dynamic TraceGuard for this version is a **report-only candidate monitor**, recording bounded possible target-owned host directories under Roaming/Local/ProgramData before and after app exit. There are no destructive cleanups, temporary profile moves, symbolic links or junctions. Source-supported data paths are redirected at their origin. Unknown or preexisting paths are never claimed as application-owned.
9. Build upstream GUI with `pnpm tauri build --ci --no-bundle` (the upstream specifically warns that plain `cargo build --release` omits Tauri production frontend features). Compile root PE with headless CMake with automatic MSVC 2022/2026 detection on GitHub's Windows runner, using **upstream's real icon** from `src-tauri/icons/icon.ico`.
10. Verify PE x64 architecture and GUI subsystem, ZIP structure/CRC, SHA-256, source completeness, upgrade sentinel and basic relocation. Run the root launcher `--self-test` unattended without starting the GUI. Publish release assets with the built-in `gh` CLI to the **same** builder repository, with no Actions artifacts.

## r2 correction: Visual Studio generator detection

GitHub moved `windows-latest` to the Visual Studio 2026 image in June 2026, while r1 required the 2022 CMake generator and failed at the launcher build (after Tauri successfully compiled and the 67 store tests passed). The new `scripts/build_launcher.ps1` uses Microsoft's preinstalled `vswhere.exe` to detect the actual x64 C++ toolchain and selects the supported CMake generator: VS 2022 -> `Visual Studio 17 2022`; VS 2026 -> `Visual Studio 18 2026`. It checks that VS 2026 has CMake 4.2 or later, verifies the upstream icon, forbids stale build directories, builds noninteractively, and verifies the resulting root EXE path. The release revision is **r2**, leaving any preexisting r1 releases untouched.

The correction changes only the **builder**, not the application's existing portable-data architecture, tray behavior, autostart choices, or TraceGuard safety policy. Windows build and interactive runtime checks must still be performed on the GitHub runner/user machine before claiming successful operation.

## GitHub Desktop: start-to-finish instructions

1. Download this builder-kit ZIP and extract it. Inside, find `README.md`, `.github/workflows/build-native.yml`, `scripts/`, `launcher/`, `manager/` and `tests/`. **Keep the `.github` folder** (Windows File Explorer may hide dot-prefixed folders in some views).
2. Open **GitHub Desktop**. Choose **File → New repository**. Name it something like `ZyntaxAI-Native-Portable-Builder`. Select any local folder and **do not** choose an existing copy of the upstream repository. Do not fork upstream. Choose whether your GitHub repository should be public or private when publishing it. Neither option changes the app's GPL redistribution obligations.
3. In GitHub Desktop, choose **Repository → Show in Explorer**. Copy all the extracted builder-kit contents into that new repository's **root**, alongside GitHub Desktop's created `.git` directory. Do **not** copy an extra outer directory and do not create `.git` yourself.
4. Return to GitHub Desktop. Inspect changed files, enter a summary such as `Add ZyntaxAI native portable builder r2`, and choose **Commit to main**.
5. Choose **Publish repository**. If you need it private, uncheck **Keep this code private** only if you **want public**. Confirm visibility carefully; distributing modified GPL binaries from private releases still entails providing corresponding source to recipients.
6. In the repository browser on GitHub, open **Settings → Actions → General**. Ensure Actions are permitted for the repository. The workflow declares `contents: write` for the same-repository GitHub Release; if repository policies override workflow permissions, adjust the repository's Workflow permissions accordingly. No personal access token or shared publisher is needed.
7. Open **Actions → Build ZyntaxAI Native Portable → Run workflow**, select `main` and click **Run workflow**. A run resolves the latest stable tagged upstream source. The builder performs tool setup, patches, source compilation, launcher compilation, validation and direct publishing unattended. It will **stop** with an error rather than silently use unverified source or skip a required file.
8. Inspect the job steps under Actions if a red failure occurs. The first meaningful error names the source anchor, dependency, test, compilation or publication stage that failed. Rerunning the same successful release will be blocked by its existing release tag; for a deliberate rebuild, update the builder revision in the source/workflow and output filename together.
9. When the run succeeds, open **Releases** in that same repository and download `ZyntaxAIPortable_<version>_Native_x64_r2.zip`. Optionally keep the Source ZIP and SHA256SUMS for verification. Public repositories have public release assets; private repositories keep release assets private to authorized members.
10. Extract the ZIP so its contained folder is exactly `X:\PortableApps\ZyntaxAIPortable\`, or any writable location you choose. Open **`ZyntaxAIPortable.exe`** (not `App\ZyntaxAI\zyntax.exe`). Windows requires the Microsoft Edge WebView2 runtime. It is generally present on Windows 10/11, but a missing runtime must be installed by its official mechanism; it is **not bundled** here.
11. Run `ZyntaxAI-Manager.cmd`. Select **1** to enable/repair Windows login startup using `ZyntaxAIPortable.exe --minimized`. Select **3** to check status or **2** to remove the managed entry. The System page in ZyntaxAI also supports toggling this entry. Settings and login startup are opt-in.
12. To upgrade, **exit ZyntaxAI completely from its tray first**, extract the newer ZIP in a temporary location, then replace the old **App** directory and root portable EXE/manager/Other files. **Do not erase or replace your existing `Data` directory.** If you moved the app, select **1** in the manager to repair the startup path.

## Portability matrix: source evidence and safe action

| Host target or integration | Evidence | Native fix | Collision/remaining limit |
|---|---|---|---|
| `ProjectDirs::from("dev", "TheHolyOneZ", "ZyntaxAI")` default config/data locations (Windows typically Roaming/Local app-specific folders; exact host paths depend on directories crate) | `crates/zyntax-store/src/paths.rs` | `ZYNTAX_DATA_DIR=<portable>/Data/ZyntaxAI`; stores `config/settings.json`, `data/history.db` and logs | Existing local installed profile left untouched; no migration without user consent |
| Windows Credential Manager service `dev.theholyonez.zyntaxai` | `crates/zyntax-store/src/secrets.rs` | Force upstream `SecretStore::file_backed`, key and encrypted data inside Data | The key is stored beside ciphertext: **not password-grade protection if drive is stolen**. Keep copies private |
| Tauri WebView2 default user-data directory, candidate `%LOCALAPPDATA%\dev.theholyonez.zyntaxai` | Tauri/WebView2 runtime defaults; original Tauri window config has no override | Windows `WebviewWindowBuilder::data_directory()` points at `Data/WebView2` | Clean-host runtime verification still needed; Windows/WebView2 system-managed traces may remain |
| Tauri window-state plugin's app-config JSON | `src-tauri/src/lib.rs` + official window-state plugin source | Remove plugin for portable flavor | Window-size/position persistence from plugin disabled; UI remains functional |
| Log files `zyntax.log` | `src-tauri/src/logging.rs` | Already reads `zyntax_store::Paths::from_env` | No app-owned logs should need host cleanup when launched via root EXE |
| Upstream Windows autostart HKCU Run | `tauri-plugin-autostart` from `lib.rs` and commands | Patch UI command to target `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\ZyntaxAIPortable` | Explicit opt-in host integration; the manager removes only a recognized own entry |
| Upstream signed in-app updater | `src-tauri/src/updates.rs` | Disable in-place install in portable mode; release download/check still possible | Update manually to protect Data; app might still display upstream update notices |
| `%PROGRAMDATA%\dev.theholyonez.zyntaxai` and nearby vendor folder | Hypothesis to check on clean host, **not source-proven program write** | Report only (TraceGuard), no ProgramData permissions requested | Do not remove or move other app/installed copy's folders |
| Temp, notification OS state, generic Windows recent execution artifacts | OS/third-party-managed | No blanket cleanup attempted | Perfect zero-trace portability cannot be guaranteed |

## TraceGuard testing and recovery

The launcher writes `Data\TraceGuard\Report.txt` after its own self-test and after normal process exit. The report shows candidate path presence before/after, but **presence does not prove ZyntaxAI created the folder**. This is deliberate: dynamically deleting a whole vendor directory would risk someone else's installed data.

For a more controlled clean Windows profile test, run `tests\TraceGuard-HostSnapshot.ps1 -Phase Before -PortableRoot <the extracted ZyntaxAIPortable folder>`, open the portable EXE, change a setting and test the hotkey, fully **Quit** the tray app, then run the same script with `-Phase After`. Compare the two JSON snapshots in `Data\TraceGuard`. The script is report-only, bounded to six target-specific candidate roots, and refuses to recursively scan broad AppData/ProgramData parents. Capture Microsoft Process Monitor events filtered to `zyntax.exe` and the specific reported path if ownership must be proven. Run tests in a disposable Windows user account to distinguish preexisting paths. Repeat after first sign-in, cache rebuild, exit and move/upgrade where relevant.

**Recovery:** No files are moved out of Data by this design, so there is no host-profile rollback transaction. If an unexpected host folder appears, do not delete it automatically. Copy your portable `Data` to safety, save the before/after snapshots and ProcMon evidence, and update the source path redirection in this builder. If data is unavailable or the drive is disconnected, the launcher fails before launching rather than switching to normal host storage.

## Verification status

- Independently inspected and source-grounded: upstream tagged v1.0.2, Rust/Tauri layout, portable path feature, secret backend, WebView2 API, autostart flag, in-app updater.
- Builder static Python unit tests: executed in the artifact-authoring environment.
- GitHub Actions execution, MSVC compilation, Rust compilation, real GUI startup, WebView2 host-path state, antivirus, signed binaries and exact PortableApps Platform integration: **NOT executed or certified here**. The supplied hosted runner workflow will exercise compilation and headless validation when you run it.
- Native GUI process can run indefinitely in tray by design: headless CI deliberately tests `--self-test` only; a Windows interactive clean-host acceptance test is required before claiming all host traces are addressed.

### Source references

- https://github.com/TheHolyOneZ/ZyntaxAI
- https://raw.githubusercontent.com/TheHolyOneZ/ZyntaxAI/v1.0.2/crates/zyntax-store/src/paths.rs
- https://raw.githubusercontent.com/TheHolyOneZ/ZyntaxAI/v1.0.2/crates/zyntax-store/src/secrets.rs
- https://raw.githubusercontent.com/TheHolyOneZ/ZyntaxAI/v1.0.2/src-tauri/src/lib.rs
- https://v2.tauri.app/reference/config/
- https://docs.rs/tauri/latest/tauri/webview/struct.WebviewWindowBuilder.html
- https://v2.tauri.app/distribute/
- https://cli.github.com/manual/gh_release_create

**Licensing:** ZyntaxAI and all derived patched upstream code are GPL-3.0-or-later (see upstream LICENSE), while this independently authored C++ launcher and builder tools are offered under MIT to the extent they are separable. Distribution of the combined executable package remains subject to upstream GPL terms. The upstream icon and trademarks remain those of their respective holders and are used for identification, not a claim of endorsement.
