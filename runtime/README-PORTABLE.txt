ZYNTAXAI NATIVE PORTABLE (UNOFFICIAL)

Launch with Launch-ZyntaxAI.cmd, NOT App\zyntax.exe.
The launcher sets ZYNTAX_DATA_DIR to this folder's Data directory.
The modified upstream app stores settings, history, logs and encrypted API keys there.
The Edge WebView2 browser data is redirected to Data\WebView2.
Window-position persistence is disabled to avoid host-profile state writes.
The portable build intentionally disables installer-based updates and Windows autostart.

UPDATING
1. Quit ZyntaxAI fully from its tray icon.
2. Download and extract the new native portable ZIP into a NEW folder.
3. Copy/move your existing Data directory to the new folder. Do NOT merge it with
   another Data directory or overwrite your secrets.key with a new one.
4. Run Launch-ZyntaxAI.cmd from the new folder.
5. Keep a backup of the old folder until everything works.

SECURITY
The portable encrypted-file backend stores the encryption key NEXT TO the
ciphertext. It prevents casual inspection, not a person who copies Data.
Protect the drive and consider BitLocker/drive encryption when using API keys.
An installed app's old credentials in Windows Credential Manager are not migrated.
Re-enter those keys in this portable edition if migrating from the installer.

LIMITATIONS
- Requires Windows 10/11 and the Microsoft Edge WebView2 Runtime on the host.
- Tauri 2.11 may create an empty default host-local application folder even
  with the WebView2 cache redirected. Windows itself records execution activity.
- Windows notifications/hotkeys and operating-system temp/cache files can still
  depend on the host's services; no claim of a zero-trace Windows session.
- Avoid running the app as administrator, from read-only folders, or from a
  cloud-sync drive that does not handle open SQLite databases safely.
- The executable is unsigned; antivirus/SmartScreen prompts remain possible.
- The upstream software is GPL-3.0-or-later; see LICENSE.txt and SOURCE-CODE.txt.
