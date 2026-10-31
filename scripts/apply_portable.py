#!/usr/bin/env python3
"""Fail-closed, source-aware portability modifications for stable ZyntaxAI Tauri 2 releases.

These edits change a disposable upstream checkout, never the developer's repo.
They deliberately fail when upstream structure changes instead of making guesses.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys


def replace_one(path: Path, old: str, new: str) -> None:
    original = path.read_text(encoding='utf-8')
    count = original.count(old)
    if count != 1:
        raise RuntimeError(f'Unexpected upstream source layout: {path} (expected 1 match, found {count})')
    path.write_text(original.replace(old, new), encoding='utf-8', newline='\n')


def replace_pattern(path: Path, pattern: str, replacement: str) -> None:
    original = path.read_text(encoding='utf-8')
    revised, matches = re.subn(pattern, replacement, original, flags=re.S)
    if matches != 1:
        raise RuntimeError(f'Unexpected upstream source layout: {path} (regex matched {matches} times)')
    path.write_text(revised, encoding='utf-8', newline='\n')


def apply(root: Path) -> None:
    config_path = root / 'src-tauri/tauri.conf.json'
    settings = json.loads(config_path.read_text(encoding='utf-8'))
    if settings.get('identifier') != 'dev.theholyonez.zyntaxai':
        raise RuntimeError('Unknown upstream Tauri app identifier; refusing portability patch')
    if settings.get('app', {}).get('appDirectoriesOverride') is not None:
        raise RuntimeError('Upstream now overrides Tauri storage; review before building')
    # Tauri 2.11.5 creates %LOCALAPPDATA%/dev.theholyonez.zyntaxai when
    # auto-created windows get the framework's default data_directory. The
    # WebView2 environment variable alone cannot stop Tauri creating this path.
    # Stop automatic creation; create BOTH original windows manually in setup
    # with WebviewWindowBuilder.data_directory set to the portable Data folder.
    # Do not alter their labels, sizing, overlay properties, or other settings.
    windows = settings.get('app', {}).get('windows', [])
    if not isinstance(windows, list) or len(windows) != 2 or {w.get('label') for w in windows} != {'main', 'overlay'}:
        raise RuntimeError('Unrecognized Tauri windows layout; review upstream before portability patch')
    for window in windows:
        if window.get('dataDirectory') or window.get('create') is False:
            raise RuntimeError('Upstream window creation/data directory was changed; review before patch')
        window['create'] = False
    # Tauri 2.11.5 does not support appDirectoriesOverride. Use its existing
    # manual window builder instead of forcing unsupported configuration.
    settings['bundle']['createUpdaterArtifacts'] = False
    config_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

    state = root / 'src-tauri/src/state.rs'
    replace_one(state,
        'let settings = AppSettings::load(&paths.settings_file())?;',
        'let mut settings = AppSettings::load(&paths.settings_file())?;\n'
        '        // Portable builds must not register Windows startup or install MSI updates.\n'
        '        settings.system.start_with_os = false;\n'
        '        settings.system.check_for_updates = false;')
    replace_one(state,
        'let secrets = SecretStore::new(paths.fallback_key_file(), paths.fallback_secrets_file());',
        '// Force the upstream AES-GCM file backend, not Windows Credential Manager.\n'
        '        let secrets = SecretStore::file_backed(paths.fallback_key_file(), paths.fallback_secrets_file());')
    replace_one(state,
        '        next.normalize();\n        next.save(&self.paths.settings_file())?;',
        '        next.normalize();\n'
        '        next.system.start_with_os = false;\n'
        '        next.system.check_for_updates = false;\n'
        '        next.save(&self.paths.settings_file())?;')

    commands = root / 'src-tauri/src/commands.rs'
    replace_one(commands, 'use tauri_plugin_autostart::ManagerExt;\n', '')
    # Patch each top-level function independently. The stable v1.0.2 source has
    # a blank line between these commands; the old combined regex assumed none.
    # (?m) anchors the function-closing brace, avoiding nested braces.
    replace_pattern(commands,
        r'(?m)^#\[tauri::command\]\npub fn set_autostart\(app: AppHandle, enabled: bool\) -> CommandResult<\(\)> \{.*?^\}',
        '''#[tauri::command]
pub fn set_autostart(app: AppHandle, enabled: bool) -> CommandResult<()> {
    let _ = (app, enabled);
    Err(simple_error(
        "portable_autostart_disabled",
        "Windows autostart is disabled in this portable edition.",
        "Launch ZyntaxAI with Launch-ZyntaxAI.cmd from your portable folder.",
    ))
}''')
    replace_pattern(commands,
        r'(?m)^#\[tauri::command\]\npub fn is_autostart_enabled\(app: AppHandle\) -> bool \{.*?^\}',
        '''#[tauri::command]
pub fn is_autostart_enabled(app: AppHandle) -> bool {
    let _ = app;
    false
}''')
    replace_pattern(commands,
        r'#\[tauri::command\]\npub async fn check_for_update\(app: AppHandle\) -> CommandResult<Option<updates::UpdateInfo>> \{.*?\n\}',
        '''#[tauri::command]
pub async fn check_for_update(_app: AppHandle) -> CommandResult<Option<updates::UpdateInfo>> {
    Err(simple_error("portable_update_disabled", "Installer updates are disabled in this portable edition.",
        "Download the next native portable ZIP from your builder repository and preserve Data."))
}''')
    replace_pattern(commands,
        r'#\[tauri::command\]\npub async fn install_update\(app: AppHandle\) -> CommandResult<\(\)> \{.*?\n\}',
        '''#[tauri::command]
pub async fn install_update(_app: AppHandle) -> CommandResult<()> {
    Err(simple_error("portable_update_disabled", "Installer updates are disabled in this portable edition.",
        "Update using the next native portable ZIP while preserving Data."))
}''')

    lib = root / 'src-tauri/src/lib.rs'
    replace_one(lib, 'use tauri_plugin_autostart::MacosLauncher;\n', '')
    replace_one(lib, '        .plugin(tauri_plugin_updater::Builder::new().build())\n', '')
    replace_pattern(lib,
        r'        \.plugin\(tauri_plugin_autostart::init\(\n.*?\n        \)\)\n',
        '')
    replace_one(lib, 'use tauri_plugin_window_state::StateFlags;\n', '')
    replace_pattern(lib,
        r'        \.plugin\(\n            tauri_plugin_window_state::Builder::default\(\).*?\n        \)\n',
        '')
    if 'tauri_plugin_window_state::Builder' in lib.read_text(encoding='utf-8'):
        raise RuntimeError('Window-state plugin unexpectedly remains registered')
    # Fail closed *before* logging::init(): upstream logging resolves Paths
    # immediately, so a direct launch without the portable environment would
    # otherwise create directories in the real host profile.
    replace_one(lib,
        '    logging::init();',
        '''    // Native portable: require portable paths BEFORE the logger writes files.
    let portable_data = std::env::var_os("ZYNTAX_DATA_DIR").unwrap_or_else(|| {
        eprintln!("Use Launch-ZyntaxAI.cmd to run the portable application.");
        std::process::exit(2);
    });
    if !std::path::PathBuf::from(portable_data).is_absolute() {
        eprintln!("Portable Data path must be absolute.");
        std::process::exit(2);
    }
    logging::init();''')
    # Both original webviews must have an explicit data_directory BEFORE build.
    # The Tauri 2.11 framework otherwise creates its default app-local directory
    # even if WEBVIEW2_USER_DATA_FOLDER overrides the WebView2 engine afterwards.
    replace_one(lib,
        '            tray::install(app)?;',
        """            // Native portable: do not create Tauri's default LocalAppData folder.
            // Both configured windows have create:false in tauri.conf.json.
            // Preserve their original config while overriding only webview storage.
            let portable_root = std::env::var_os("ZYNTAX_DATA_DIR").ok_or_else(|| {
                std::io::Error::new(
                    std::io::ErrorKind::NotFound,
                    "Launch ZyntaxAI using Launch-ZyntaxAI.cmd (missing ZYNTAX_DATA_DIR)",
                )
            })?;
            let portable_root = std::path::PathBuf::from(portable_root);
            if !portable_root.is_absolute() {
                return Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidInput,
                    "ZYNTAX_DATA_DIR must be an absolute directory",
                ).into());
            }
            let browser_data = portable_root.join("WebView2");
            std::fs::create_dir_all(&browser_data)?;
            for window_config in &app.config().app.windows {
                tauri::WebviewWindowBuilder::from_config(app, window_config)?
                    .data_directory(browser_data.clone())
                    .build()?;
            }
            tray::install(app)?;""")
    # Ensure the main entry still uses the supported Tauri-generated frontend/context.
    assert '.build(tauri::generate_context!())' in lib.read_text(encoding='utf-8')
    print('Portable patch applied: both Tauri windows create=false with explicit Data/WebView2 storage, file credentials, guarded OS integration/updates.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python scripts/apply_portable.py PATH_TO_UPSTREAM_SOURCE')
    try:
        apply(Path(sys.argv[1]).resolve(strict=True))
    except (RuntimeError, OSError, KeyError, ValueError, AssertionError) as exc:
        sys.exit(f'ERROR applying portable patches: {exc}')
