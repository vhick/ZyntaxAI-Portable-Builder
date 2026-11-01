"""Offline simulated test fixtures. This suite is NOT proof of Windows execution."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import apply_portable
import package_release
import validate_packages
import resolve_upstream
import fix_shared_publisher


class SourcePatchTests(unittest.TestCase):
    def test_v102_source_layout_patches_and_disables_host_window_state(self):
        with TemporaryDirectory() as temp:
            src = Path(temp)
            tauri = src / 'src-tauri'
            tauri.mkdir()
            (tauri / 'tauri.conf.json').write_text(json.dumps({
                'identifier': 'dev.theholyonez.zyntaxai', 'app': {'windows': [{'label':'main','url':'index.html','width':940}, {'label':'overlay','url':'overlay.html','visible':False,'alwaysOnTop':True}]},
                'bundle': {'createUpdaterArtifacts': True}
            }), encoding='utf-8')
            rust = tauri / 'src'
            rust.mkdir()
            (rust / 'state.rs').write_text('''
        let settings = AppSettings::load(&paths.settings_file())?;
        let secrets = SecretStore::new(paths.fallback_key_file(), paths.fallback_secrets_file());
        next.normalize();
        next.save(&self.paths.settings_file())?;
''', encoding='utf-8')
            (rust / 'commands.rs').write_text('''
use tauri_plugin_autostart::ManagerExt;
#[tauri::command]
pub fn set_autostart(app: AppHandle, enabled: bool) -> CommandResult<()> {
    let manager = app.autolaunch();
    let result = if enabled {
        manager.enable()
    } else {
        manager.disable()
    };
    result.map_err(|err| simple_error("autostart_failed", err.to_string(), "error"))
}

#[tauri::command]
pub fn is_autostart_enabled(app: AppHandle) -> bool {
    app.autolaunch().is_enabled().unwrap_or(false)
}
#[tauri::command]
pub async fn check_for_update(app: AppHandle) -> CommandResult<Option<updates::UpdateInfo>> {
    updates::check(&app).await
}
#[tauri::command]
pub async fn install_update(app: AppHandle) -> CommandResult<()> {
    updates::install(&app).await
}
''', encoding='utf-8')
            (rust / 'lib.rs').write_text('''
use tauri_plugin_autostart::MacosLauncher;
use tauri_plugin_window_state::StateFlags;
    logging::init();
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(
            tauri_plugin_window_state::Builder::default()
                 .build(),
        )
        .plugin(tauri_plugin_autostart::init(
            MacosLauncher::LaunchAgent,
            Some(vec![ARG_MINIMIZED]),
        ))
            tray::install(app)?;
        .build(tauri::generate_context!())
''', encoding='utf-8')
            apply_portable.apply(src)
            cfg = json.loads((tauri / 'tauri.conf.json').read_text())
            self.assertNotIn('appDirectoriesOverride', cfg['app'])
            self.assertEqual([w['label'] for w in cfg['app']['windows']], ['main','overlay'])
            self.assertTrue(all(w['create'] is False for w in cfg['app']['windows']))
            self.assertEqual(cfg['app']['windows'][0]['width'], 940)
            self.assertEqual(cfg['app']['windows'][1]['url'], 'overlay.html')
            self.assertTrue(cfg['app']['windows'][1]['alwaysOnTop'])
            self.assertFalse(cfg['app']['windows'][1]['visible'])
            state = (rust / 'state.rs').read_text()
            self.assertIn('SecretStore::file_backed', state)
            self.assertIn('next.system.check_for_updates = false', state)
            cmds = (rust / 'commands.rs').read_text()
            self.assertIn('portable_autostart_disabled', cmds)
            self.assertNotIn('app.autolaunch()', cmds)
            self.assertIn('pub fn is_autostart_enabled(app: AppHandle)', cmds)
            self.assertIn('portable_update_disabled', cmds)
            lib = (rust / 'lib.rs').read_text()
            self.assertNotIn('.plugin(tauri_plugin_updater::Builder', lib)
            self.assertNotIn('.plugin(tauri_plugin_autostart::init', lib)
            self.assertNotIn('tauri_plugin_window_state::Builder', lib)
            self.assertNotIn('use tauri_plugin_window_state::StateFlags;', lib)
            self.assertIn('WebviewWindowBuilder::from_config(app, window_config)?', lib)
            self.assertIn('.data_directory(browser_data.clone())', lib)
            self.assertIn('for window_config in &app.config().app.windows', lib)
            self.assertIn('std::env::var_os("ZYNTAX_DATA_DIR")', lib)
            self.assertIn('Use Launch-ZyntaxAI.cmd to run the portable application.', lib)
            self.assertLess(lib.index('Use Launch-ZyntaxAI.cmd'), lib.index('logging::init();'))
            self.assertLess(lib.index('.data_directory(browser_data.clone())'), lib.index('tray::install(app)?'))
            with self.assertRaises(RuntimeError):
                apply_portable.apply(src)  # must fail on already modified source

    def test_tauri_windows_regression_guards_present(self):
        patch = (ROOT / 'scripts/apply_portable.py').read_text(encoding='utf-8')
        self.assertIn("{'main', 'overlay'}", patch)
        self.assertIn("window['create'] = False", patch)
        self.assertIn('WebviewWindowBuilder::from_config', patch)
        self.assertIn('app.config().app.windows', patch)
        self.assertNotIn("settings['app']['appDirectoriesOverride']", patch)

    def test_v102_autostart_regression_real_source_snippet(self):
        """Official release includes a blank line and nested Rust blocks.

        The combined v1.0 matcher incorrectly assumed both commands were
        adjacent, which is why that workflow failed at regex matched 0 times.
        """
        original = """#[tauri::command]
pub fn set_autostart(app: AppHandle, enabled: bool) -> CommandResult<()> {
    let manager = app.autolaunch();
    let result = if enabled {
        manager.enable()
    } else {
        manager.disable()
    };

    result.map_err(|err| {
        simple_error(
            "autostart_failed",
            err.to_string(),
            "This is the official upstream-style multiline function body",
        )
    })
}

#[tauri::command]
pub fn is_autostart_enabled(app: AppHandle) -> bool {
    app.autolaunch().is_enabled().unwrap_or(false)
}

#[tauri::command]
pub fn app_version() -> String {
    env!("CARGO_PKG_VERSION").to_owned()
}
"""
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'commands.rs'
            path.write_text(original, encoding='utf-8')
            apply_portable.replace_pattern(
                path,
                r'(?m)^#\[tauri::command\]\npub fn set_autostart\(app: AppHandle, enabled: bool\) -> CommandResult<\(\)> \{.*?^\}',
                'REPLACED_AUTOSTART',
            )
            apply_portable.replace_pattern(
                path,
                r'(?m)^#\[tauri::command\]\npub fn is_autostart_enabled\(app: AppHandle\) -> bool \{.*?^\}',
                'REPLACED_CHECK',
            )
            final = path.read_text(encoding='utf-8')
            self.assertEqual(final.count('REPLACED_AUTOSTART'), 1)
            self.assertEqual(final.count('REPLACED_CHECK'), 1)
            self.assertIn('pub fn app_version()', final)
            self.assertNotIn('app.autolaunch()', final)

    def test_tag_and_asset_names_are_deterministic(self):
        meta = {'version': '1.0.2', 'revision': 'r1'}
        names = resolve_upstream.expected_zip_names(meta)
        self.assertEqual(names, {
            'ZyntaxAI-Native-Portable-1.0.2-r1-win64.zip',
            'ZyntaxAI-Portable-Source-1.0.2-r1-win64.zip',
        })
        self.assertTrue(resolve_upstream.TAG_PATTERN.fullmatch('v1.0.2'))
        self.assertFalse(resolve_upstream.TAG_PATTERN.fullmatch('v1.0.3-beta.1'))


class PackagingTests(unittest.TestCase):
    def test_packaging_and_zip_validation_fixture(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.work/upstream/target/release').mkdir(parents=True)
            (root / '.work/upstream/target/release/zyntax.exe').write_bytes(b'MZ' + b'\0' * 100_002)
            upstream = root / '.work/upstream'
            for name in ['LICENSE', 'Cargo.lock', 'pnpm-lock.yaml']:
                (upstream / name).write_text('fixture ' + name, encoding='utf-8')
            (root / 'runtime').mkdir()
            for name in ['Launch-ZyntaxAI.cmd', 'ZyntaxAI-Manager.cmd', 'README-PORTABLE.txt']:
                (root / 'runtime' / name).write_text('test fixture', encoding='utf-8')
            for name in ['BUILDER_REVISION', '.github/workflows/build-portable.yml',
                         'scripts/resolve_upstream.py', 'scripts/apply_portable.py',
                         'scripts/package_release.py', 'scripts/validate_packages.py',
                         'scripts/verify_release.py', 'scripts/fix_shared_publisher.py', 'README.md']:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text('test fixture', encoding='utf-8')
            meta = {'version': '1.0.2', 'revision': 'r1', 'tag': 'portable-v1.0.2-uaaaaa-r1-pbbbbb',
                    'upstream_tag': 'v1.0.2', 'upstream': 'TheHolyOneZ/ZyntaxAI',
                    'upstream_commit': 'a' * 40, 'portable_zip': 'ZyntaxAI-Native-Portable-1.0.2-r1-win64.zip',
                    'source_zip': 'ZyntaxAI-Portable-Source-1.0.2-r1-win64.zip'}
            (root / '.work/build-meta.json').write_text(json.dumps(meta), encoding='utf-8')
            old = [package_release.ROOT, package_release.WORK, package_release.DIST, package_release.SOURCE, validate_packages.ROOT]
            try:
                package_release.ROOT = root
                package_release.WORK = root / '.work'
                package_release.DIST = root / 'dist'
                package_release.SOURCE = upstream
                validate_packages.ROOT = root
                package_release.package()
                validate_packages.validate()
                with zipfile.ZipFile(root / 'dist' / meta['portable_zip']) as z:
                    self.assertEqual(z.read('App/zyntax.exe')[:2], b'MZ')
                    self.assertIn('Data/.keep', z.namelist())
                self.assertEqual(len(list((root / 'dist').glob('*.zip'))), 2)
            finally:
                (package_release.ROOT, package_release.WORK, package_release.DIST, package_release.SOURCE, validate_packages.ROOT) = old


if __name__ == '__main__':
    unittest.main()


class SharedPublisherWindowsFixTests(unittest.TestCase):
    """Regression tests against the real @v1 source pattern seen in GitHub's raw file."""

    def test_checksum_file_is_platform_independent_after_patch(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'scripts').mkdir()
            (root / 'action.yml').write_text('runs:\n  using: composite\nPUBLISH_FILES: test\n', encoding='utf-8')
            text = '''def remote_assets_match():
    pass

def verify_new_draft():
    pass

checksum_path.write_text(sums, encoding="utf-8")
'''
            script = root / 'scripts/publish.py'
            script.write_text(text, encoding='utf-8')
            fix_shared_publisher.patch(root)
            patched = script.read_text(encoding='utf-8')
            self.assertIn('checksum_path.write_bytes(sums.encode("utf-8"))', patched)
            self.assertNotIn('checksum_path.write_text(sums, encoding="utf-8")', patched)
            # Windows text-mode would add two CR bytes for two checksum lines,
            # while the publisher's expected byte size uses UTF-8 LF only.
            sums = ('a' * 64 + '  first.zip\n') + ('b' * 64 + '  second.zip\n')
            self.assertEqual(len(sums.replace('\n', '\r\n').encode()), len(sums.encode()) + 2)
            self.assertEqual(len(sums.encode()), len(sums.encode('utf-8')))
            with self.assertRaisesRegex(RuntimeError, 'not found exactly once'):
                fix_shared_publisher.patch(root)

    def test_unknown_shared_publisher_version_stops_early(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'scripts').mkdir()
            (root / 'action.yml').write_text('runs:\n  using: composite\nPUBLISH_FILES: test\n', encoding='utf-8')
            (root / 'scripts/publish.py').write_text('not the audited publisher', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'not found exactly once'):
                fix_shared_publisher.patch(root)


class PortableManagerAutostartTests(unittest.TestCase):
    """Static checks only: registry behavior requires an actual Windows login."""

    def test_opt_in_autostart_menu_and_registry_scope(self):
        manager = (ROOT / 'runtime/ZyntaxAI-Manager.cmd').read_text(encoding='utf-8')
        self.assertIn('choice /c 123456780', manager)
        self.assertIn('8. Inspect leftover LocalAppData folder', manager)
        self.assertIn('rmdir "%RESIDUE%"', manager)
        self.assertNotIn('rmdir /s', manager.lower())
        for option in ('5. Enable Windows login autostart',
                       '6. Disable Windows login autostart',
                       '7. Show Windows login autostart status'):
            self.assertIn(option, manager)
        self.assertIn(r'HKCU\Software\Microsoft\Windows\CurrentVersion\Run', manager)
        self.assertIn('ZyntaxAI-Native-Portable', manager)
        self.assertIn('/t REG_SZ', manager)
        self.assertIn('reg add "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%"', manager)
        self.assertIn('reg delete "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%" /f', manager)
        self.assertIn('reg query "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%"', manager)
        self.assertIn(r'%~dp0Launch-ZyntaxAI.cmd', manager)
        self.assertIn('/d /c', manager)
        self.assertNotIn('reg add "HKLM', manager.lower())
        self.assertNotIn('schtasks /create', manager.lower())
        self.assertNotIn('runas', manager.lower())
        self.assertNotIn('executionpolicy', manager.lower())

    def test_tray_autostart_passes_supported_argument(self):
        manager = (ROOT / 'runtime/ZyntaxAI-Manager.cmd').read_text(encoding='utf-8')
        self.assertIn('Launch-ZyntaxAI.cmd\\" --minimized', manager)
        self.assertIn('MODE: System tray startup [--minimized]', manager)
        self.assertIn('MODE: Legacy startup entry', manager)
        self.assertIn('findstr /l /c:"--minimized"', manager)
        self.assertIn('Select option 5 to update', manager)
        self.assertNotIn('powershell -enc', manager.lower())
        self.assertNotIn('wscript', manager.lower())
        self.assertNotIn('start /min', manager.lower())
        launcher = (ROOT / 'runtime/Launch-ZyntaxAI.cmd').read_text(encoding='utf-8')
        self.assertIn('start "" "%ZYNTAX_EXE%" %*', launcher)

    def test_portable_launcher_unchanged_and_preserves_data(self):
        launcher = (ROOT / 'runtime/Launch-ZyntaxAI.cmd').read_text(encoding='utf-8')
        self.assertIn('ZYNTAX_DATA_DIR=%PORTABLE_ROOT%Data', launcher)
        self.assertIn(r'WEBVIEW2_USER_DATA_FOLDER=%PORTABLE_ROOT%Data\WebView2', launcher)
        self.assertIn('start "" "%ZYNTAX_EXE%" %*', launcher)
        self.assertEqual((ROOT / 'BUILDER_REVISION').read_text().strip(), 'r6')
