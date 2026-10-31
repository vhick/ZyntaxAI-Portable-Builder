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
    # The official upstream lockfile pins Tauri 2.11.5; appDirectoriesOverride was
    # introduced in 2.12.0. Never inject an unsupported configuration field.
    # WEBVIEW2_USER_DATA_FOLDER is passed by the launcher as a documented WebView2
    # environment override. Disable the window-state plugin below because it would
    # otherwise write to the host's Tauri app-config directory.
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
    replace_pattern(commands,
        r'#\[tauri::command\]\npub fn set_autostart\(app: AppHandle, enabled: bool\) -> CommandResult<\(\)> \{.*?\n\}\n#\[tauri::command\]\npub fn is_autostart_enabled\(app: AppHandle\) -> bool \{.*?\n\}',
        '''#[tauri::command]
pub fn set_autostart(_app: AppHandle, _enabled: bool) -> CommandResult<()> {
    Err(simple_error(
        "portable_autostart_disabled",
        "Windows autostart is disabled in this portable edition.",
        "Launch ZyntaxAI with Launch-ZyntaxAI.cmd from your portable folder.",
    ))
}
#[tauri::command]
pub fn is_autostart_enabled(_app: AppHandle) -> bool {
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
    # Ensure the main entry still uses the supported Tauri-generated frontend/context.
    assert '.build(tauri::generate_context!())' in lib.read_text(encoding='utf-8')
    print('Portable patch applied: upstream data API, file-backed credentials, WebView2 runtime override, disabled window-state persistence, guarded OS integration and updates.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python scripts/apply_portable.py PATH_TO_UPSTREAM_SOURCE')
    try:
        apply(Path(sys.argv[1]).resolve(strict=True))
    except (RuntimeError, OSError, KeyError, ValueError, AssertionError) as exc:
        sys.exit(f'ERROR applying portable patches: {exc}')
