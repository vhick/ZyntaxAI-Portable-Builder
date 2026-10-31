@echo off
setlocal DisableDelayedExpansion
rem ZyntaxAI native portable manager: normal user, explicit Windows login integration.
rem Only this named HKCU Run value is modified. No services, tasks, or elevation.
set "AUTOSTART_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "AUTOSTART_VALUE=ZyntaxAI-Native-Portable"

:menu
cls
echo ===========================================================
echo  ZyntaxAI Native Portable Manager
echo ===========================================================
echo   1. Launch ZyntaxAI
echo   2. Open portable Data folder
echo   3. Open application logs
echo   4. Show portable paths and diagnostics
echo   5. Enable Windows login autostart [current user]
echo   6. Disable Windows login autostart
echo   7. Show Windows login autostart status
echo   8. Inspect leftover LocalAppData folder
echo   0. Exit manager (does NOT stop ZyntaxAI)
echo.
choice /c 123456780 /n /m "Choose: "
if errorlevel 9 exit /b 0
if errorlevel 8 goto residue
if errorlevel 7 goto autostart_status
if errorlevel 6 goto autostart_disable
if errorlevel 5 goto autostart_enable
if errorlevel 4 goto diagnostics
if errorlevel 3 goto logs
if errorlevel 2 goto data
if errorlevel 1 goto launch
goto menu

:launch
call "%~dp0Launch-ZyntaxAI.cmd"
goto menu

:data
if not exist "%~dp0Data" mkdir "%~dp0Data" 2>nul
start "" "%~dp0Data"
goto menu

:logs
if not exist "%~dp0Data\data\logs" mkdir "%~dp0Data\data\logs" 2>nul
start "" "%~dp0Data\data\logs"
goto menu

:diagnostics
cls
echo Portable application root: "%~dp0"
echo Application executable: "%~dp0App\zyntax.exe"
echo Configuration: "%~dp0Data\config\settings.json"
echo History: "%~dp0Data\data\history.db"
echo Logs: "%~dp0Data\data\logs"
echo WebView2 browser cache: "%~dp0Data\WebView2"
echo Both Tauri webviews: explicit portable data directory (new builds)
if exist "%LOCALAPPDATA%\dev.theholyonez.zyntaxai" (echo NOTICE: Old host-local directory remains; choose option 8 to inspect.) else (echo No old host-local ZyntaxAI directory detected.)
echo Window position persistence: Disabled to avoid profile writes
echo.
if exist "%~dp0App\zyntax.exe" (echo Application EXE found.) else (echo WARNING: Missing application EXE.)
reg query "HKLM\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F1E7E4F1-DA6C-4A73-9BC2-835921A027D6}" /v pv >nul 2>&1
if errorlevel 1 (echo WebView2 Runtime: Not confirmed by registry; application may still work if runtime is installed elsewhere.) else (echo WebView2 Runtime: Registry installation detected.)
echo.
call :show_autostart_status
echo This manager does not install services or scheduled tasks.
echo.
pause
goto menu

:autostart_enable
cls
echo ENABLE WINDOWS LOGIN AUTOSTART
echo.
if not exist "%~dp0Launch-ZyntaxAI.cmd" (
    echo ERROR: Missing Launch-ZyntaxAI.cmd in this portable folder.
    pause
    goto menu
)
if not exist "%~dp0App\zyntax.exe" (
    echo ERROR: Missing App\zyntax.exe. Complete the portable application first.
    pause
    goto menu
)
echo Registers ONE current-user Windows startup entry. No administrator access.
echo The entry runs Launch-ZyntaxAI.cmd so ZYNTAX_DATA_DIR stays portable.
echo.
reg query "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%" >nul 2>&1
if not errorlevel 1 (
    echo An entry with this name already exists:
    reg query "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%"
    echo.
    choice /c YN /n /m "Replace it with the launcher in THIS folder? [Y/N]: "
    if errorlevel 2 goto menu
)
rem Backslash-escaped quotes make reg.exe store literal quotation marks.
rem Registered command is: "cmd.exe" /d /c ""FULL_PATH\Launch-ZyntaxAI.cmd""
rem cmd /d prevents unrelated Command Processor AutoRun hooks.
reg add "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%" /t REG_SZ /d "\"%SystemRoot%\System32\cmd.exe\" /d /c \"\"%~dp0Launch-ZyntaxAI.cmd\"\"" /f >nul
if errorlevel 1 (
    echo ERROR: Could not register Windows login autostart.
    echo Ensure this is your normal Windows account, then try again.
) else (
    echo Autostart entry registered successfully for the current Windows user.
    echo It will run at the NEXT login. Windows may show a brief CMD window.
    echo NOTE: Moving this portable folder requires selecting Enable again.
)
echo.
call :show_autostart_status
pause
goto menu

:autostart_disable
cls
echo DISABLE WINDOWS LOGIN AUTOSTART
echo.
reg query "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%" >nul 2>&1
if errorlevel 1 (
    echo No ZyntaxAI Native Portable autostart entry was found.
    pause
    goto menu
)
echo Existing entry:
reg query "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%"
echo.
choice /c YN /n /m "Remove ONLY this ZyntaxAI autostart entry? [Y/N]: "
if errorlevel 2 goto menu
reg delete "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%" /f >nul
if errorlevel 1 (
    echo ERROR: Unable to remove the autostart entry.
) else (
    echo ZyntaxAI Windows login autostart entry removed.
    echo ZyntaxAI, if running, remains running until you exit it normally.
)
echo.
pause
goto menu

:autostart_status
cls
call :show_autostart_status
echo.
pause
goto menu

:show_autostart_status
echo Windows login startup registration for CURRENT user:
reg query "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%" >nul 2>&1
if errorlevel 1 (
    echo NOT REGISTERED: ZyntaxAI Native Portable is not set to start at login.
) else (
    echo REGISTERED: Windows has the following startup command:
    reg query "%AUTOSTART_KEY%" /v "%AUTOSTART_VALUE%"
    echo.
    echo If its folder path is outdated, choose option 5 to register this copy.
    echo Windows Startup Apps settings may separately disable a registered entry.
)
exit /b 0

:residue
cls
set "RESIDUE=%LOCALAPPDATA%\dev.theholyonez.zyntaxai"
echo LEGACY HOST LOCALAPPDATA INSPECTION
echo.
echo Host path: "%RESIDUE%"
echo This is NOT the portable Data folder.
echo.
if not exist "%RESIDUE%\" (
    echo No residual ZyntaxAI folder found in LocalAppData.
    pause
    goto menu
)
echo Files and folders currently present:
dir /a "%RESIDUE%"
echo.
echo The manager will NOT delete nonempty data or follow links.
echo Make sure ZyntaxAI is completely exited before any cleanup.
echo.
choice /c YN /n /m "Try removing this folder ONLY if it is empty? [Y/N]: "
if errorlevel 2 goto menu
rem rmdir WITHOUT /s refuses to delete nonempty folders; no data loss.
rmdir "%RESIDUE%" 2>nul
if exist "%RESIDUE%\" (
    echo Folder is not empty, in use, or cannot be removed.
    echo Review its contents and back up important files before manual removal.
    echo The manager does not delete nonempty profile data.
) else (
    echo Empty host-local directory removed successfully.
)
echo.
pause
goto menu
