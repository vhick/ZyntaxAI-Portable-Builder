#!/usr/bin/env python3
"""Fail-closed, repeatable source changes for ZyntaxAI native Windows portability.

Runs only on a separate checkout of a verified stable upstream Git tag.
Never modifies upstream's original repository on GitHub.
"""
import argparse
import json
import pathlib
import re


def replace_once(text, before, after, location):
    count = text.count(before)
    if count != 1:
        raise RuntimeError(f'{location}: expected exactly one upstream anchor, found {count}; stop and audit the new release')
    return text.replace(before, after, 1)


def patch(directory):
    base = pathlib.Path(directory).resolve()
    config_file = base / 'src-tauri/tauri.conf.json'
    raw_config = config_file.read_text(encoding='utf-8')
    cfg = json.loads(raw_config)
    if cfg['identifier'] != 'dev.theholyonez.zyntaxai':
        raise RuntimeError('Upstream application identity changed; audit required')
    windows = cfg['app']['windows']
    if sorted(w['label'] for w in windows) != ['main', 'overlay']:
        raise RuntimeError('Upstream window structure changed; audit required')
    for w in windows:
        w['create'] = False
        w['visible'] = False
    config_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    lib_file = base / 'src-tauri/src/lib.rs'
    lib = lib_file.read_text(encoding='utf-8')
    pattern = r'\n\s*\.plugin\(\s*tauri_plugin_window_state::Builder::default\(\).*?\.build\(\),\s*\)'
    lib, count = re.subn(pattern, '', lib, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError('Upstream window-state plugin registration changed; audit required')
    lib = replace_once(lib, 'use tauri_plugin_window_state::StateFlags;\n', '', 'lib.rs')
    setup_insert = '''        .setup(move |app| {
            // The portable launcher owns this path. No host AppData directory is used
            // for either main or overlay WebView2 storage on Windows.
            let webview_dir = std::env::var_os("ZYNTAX_PORTABLE_WEBVIEW_DIR")
                .ok_or_else(|| std::io::Error::other("portable WebView2 path is missing"))?;
            let webview_dir = std::path::PathBuf::from(webview_dir);
            std::fs::create_dir_all(&webview_dir)?;
            for window_config in &app.config().app.windows {
                tauri::WebviewWindowBuilder::from_config(app.handle(), window_config)?
                    .data_directory(webview_dir.clone())
                    .build()?;
            }
'''
    lib = replace_once(lib, '        .setup(move |app| {\n', setup_insert, 'lib.rs')
    lib_file.write_text(lib, encoding='utf-8')

    state_file = base / 'src-tauri/src/state.rs'
    state = state_file.read_text(encoding='utf-8')
    state = replace_once(
        state,
        '        let secrets = SecretStore::new(paths.fallback_key_file(), paths.fallback_secrets_file());',
        '''        // Portable builds must never store API credentials in Windows Credential Manager.
        let secrets = if std::env::var_os("ZYNTAX_PORTABLE_MODE").is_some() {
            SecretStore::file_backed(paths.fallback_key_file(), paths.fallback_secrets_file())
        } else {
            SecretStore::new(paths.fallback_key_file(), paths.fallback_secrets_file())
        };''',
        'state.rs')
    state_file.write_text(state, encoding='utf-8')

    updates_file = base / 'src-tauri/src/updates.rs'
    updates = updates_file.read_text(encoding='utf-8')
    updates = replace_once(
        updates, 'fn can_install_in_place() -> bool {\n',
        '''fn can_install_in_place() -> bool {
    // Upstream's MSI/updater replacement mechanism must not overwrite portable binaries/Data.
    if std::env::var_os("ZYNTAX_PORTABLE_MODE").is_some() {
        return false;
    }
''', 'updates.rs')
    updates_file.write_text(updates, encoding='utf-8')

    commands_file = base / 'src-tauri/src/commands.rs'
    commands = commands_file.read_text(encoding='utf-8')
    commands = replace_once(commands,
        '''pub fn set_autostart(app: AppHandle, enabled: bool) -> CommandResult<()> {
''',
        '''pub fn set_autostart(app: AppHandle, enabled: bool) -> CommandResult<()> {
    #[cfg(target_os = "windows")]
    if std::env::var_os("ZYNTAX_PORTABLE_MODE").is_some() {
        return portable_autostart_set(enabled).map_err(|err| simple_error(
            "autostart_failed", err.to_string(),
            "Check permission to change your own HKCU Run entry, or use ZyntaxAI-Manager.cmd.",
        ));
    }
''', 'commands.rs')
    commands = replace_once(commands,
        '''pub fn is_autostart_enabled(app: AppHandle) -> bool {
''',
        '''pub fn is_autostart_enabled(app: AppHandle) -> bool {
    #[cfg(target_os = "windows")]
    if std::env::var_os("ZYNTAX_PORTABLE_MODE").is_some() {
        return portable_autostart_enabled();
    }
''', 'commands.rs')
    registry_helpers = r'''
#[cfg(target_os = "windows")]
const PORTABLE_RUN_KEY: &str = "Software\\Microsoft\\Windows\\CurrentVersion\\Run";
#[cfg(target_os = "windows")]
const PORTABLE_RUN_NAME: &str = "ZyntaxAIPortable";

#[cfg(target_os = "windows")]
fn portable_launcher_path() -> std::io::Result<std::path::PathBuf> {
    let exe = std::env::current_exe()?;
    // Package: root/App/ZyntaxAI/zyntax.exe -> root/ZyntaxAIPortable.exe
    let root = exe.parent().and_then(|p| p.parent()).and_then(|p| p.parent())
        .ok_or_else(|| std::io::Error::other("portable directory is missing"))?;
    let launcher = root.join("ZyntaxAIPortable.exe");
    if !launcher.is_file() {
        return Err(std::io::Error::other("root ZyntaxAIPortable.exe is missing"));
    }
    Ok(launcher)
}

#[cfg(target_os = "windows")]
fn portable_run_command() -> std::io::Result<String> {
    Ok(format!("\"{}\" --minimized", portable_launcher_path()?.display()))
}

#[cfg(target_os = "windows")]
fn portable_autostart_set(enable: bool) -> std::io::Result<()> {
    use winreg::enums::HKEY_CURRENT_USER;
    use winreg::RegKey;
    let hive = RegKey::predef(HKEY_CURRENT_USER);
    if enable {
        let (key, _) = hive.create_subkey(PORTABLE_RUN_KEY)?;
        if let Ok(existing) = key.get_value::<String, _>(PORTABLE_RUN_NAME) {
            // Never overwrite an unrelated entry accidentally using our entry name.
            if !existing.to_ascii_lowercase().contains("zyntaxaiportable.exe") {
                return Err(std::io::Error::new(std::io::ErrorKind::AlreadyExists,
                    "the startup registry value is owned by another application"));
            }
        }
        key.set_value(PORTABLE_RUN_NAME, &portable_run_command()?)
    } else {
        let Ok(key) = hive.open_subkey_with_flags(PORTABLE_RUN_KEY, winreg::enums::KEY_READ | winreg::enums::KEY_SET_VALUE) else {
            return Ok(());
        };
        if let Ok(existing) = key.get_value::<String, _>(PORTABLE_RUN_NAME) {
            if !existing.to_ascii_lowercase().contains("zyntaxaiportable.exe") {
                return Err(std::io::Error::other("startup entry is not recognized as ours"));
            }
            key.delete_value(PORTABLE_RUN_NAME)?;
        }
        Ok(())
    }
}

#[cfg(target_os = "windows")]
fn portable_autostart_enabled() -> bool {
    use winreg::enums::HKEY_CURRENT_USER;
    use winreg::RegKey;
    RegKey::predef(HKEY_CURRENT_USER).open_subkey(PORTABLE_RUN_KEY).ok()
        .and_then(|k| k.get_value::<String, _>(PORTABLE_RUN_NAME).ok())
        .and_then(|command| portable_run_command().ok()
            .map(|expected| command.eq_ignore_ascii_case(&expected)))
        .unwrap_or(false)
}
'''
    commands = replace_once(commands, '#[tauri::command]\npub fn app_version() -> String {',
        registry_helpers + '\n#[tauri::command]\npub fn app_version() -> String {', 'commands.rs')
    commands_file.write_text(commands, encoding='utf-8')

    cargo_file = base / 'src-tauri/Cargo.toml'
    cargo = cargo_file.read_text(encoding='utf-8')
    cargo += '\n[target.\'cfg(target_os = "windows")\'.dependencies]\nwinreg = "0.55"\n'
    cargo_file.write_text(cargo, encoding='utf-8')

    checks = {
        'windows_created_manually': all(not x['create'] for x in cfg['app']['windows']),
        'webview_portable_directory': 'ZYNTAX_PORTABLE_WEBVIEW_DIR' in lib,
        'windows_state_plugin_removed': 'tauri_plugin_window_state::Builder::default()' not in lib,
        'file_backed_credentials': 'SecretStore::file_backed' in state,
        'updater_disallowed': 'return false;' in updates,
        'autostart_portable_launcher': 'portable_autostart_set' in commands,
    }
    if not all(checks.values()):
        raise RuntimeError(f'Portability assertion failed: {checks}')
    print(json.dumps(checks, indent=2))
    return checks


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', required=True)
    args = parser.parse_args()
    patch(args.upstream)
