ZYNTAXAI NATIVE PORTABLE (UNOFFICIAL)

Launch with Launch-ZyntaxAI.cmd, NOT App\zyntax.exe.
The v1.4 compiled app refuses direct launches without ZYNTAX_DATA_DIR
before logger startup to avoid writing into the host user profile.
The launcher sets ZYNTAX_DATA_DIR to this folder's Data directory.
The modified upstream app stores settings, history, logs and encrypted API keys there.
The Edge WebView2 browser data is redirected to Data\WebView2.
Both original Tauri windows are created manually with the same explicit
portable directory, preventing their default LocalAppData folder creation.
Window-position persistence is disabled to avoid host-profile state writes.
The portable build intentionally disables installer-based updates and the
upstream in-app Windows autostart plugin. Optional autostart is available in
ZyntaxAI-Manager.cmd instead. It registers only one current-user Windows Run
value that calls Launch-ZyntaxAI.cmd --minimized (not the EXE directly).

WINDOWS LOGIN AUTOSTART (OPTIONAL)
Open ZyntaxAI-Manager.cmd in your portable folder:
  5 - Enable Windows login autostart in the SYSTEM TRAY
  6 - Disable/remove the login autostart entry
  7 - Inspect entry, launch path, and startup mode
  8 - Inspect any leftover old LocalAppData folder; only remove if empty
The manager uses HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Value name: ZyntaxAI-Native-Portable
No administrator permission, service, or scheduled task is required.
Startup begins when you sign in to Windows (not at power-on before login).
The console may briefly appear when Windows starts the CMD launcher.
The --minimized argument is supported by upstream ZyntaxAI: it keeps the
main window hidden at sign-in while the system tray icon remains available.
Manual launches without --minimized open the main Settings window normally.
If you already enabled autostart in an older manager, select 5 again and
confirm replacement so that Windows receives the new --minimized argument.
If you MOVE the portable folder, choose 5 again so Windows uses the new path.
If you move it to a new computer, enable autostart on that computer separately.
Before deleting a portable folder, choose 6 to remove its Windows startup entry.
Windows Settings > Apps > Startup can independently disable registered apps.
The in-app Start with Windows setting remains intentionally disabled; use the
manager for the portable build. The manager does not auto-enable autostart.


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
- New builds prevent Tauri's default WebView directory creation using
  manual windows and an explicit portable data-directory override. Existing
  host-profile leftovers from older builds are not automatically removed.
  Use manager option 8 to inspect them and remove an empty folder only.
  Windows itself still records execution activity.
- Windows notifications/hotkeys and operating-system temp/cache files can still
  depend on the host's services; no claim of a zero-trace Windows session.
- Avoid running the app as administrator, from read-only folders, or from a
  cloud-sync drive that does not handle open SQLite databases safely.
- The executable is unsigned; antivirus/SmartScreen prompts remain possible.
- The upstream software is GPL-3.0-or-later; see LICENSE.txt and SOURCE-CODE.txt.
