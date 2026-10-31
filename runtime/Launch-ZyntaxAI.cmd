@echo off
setlocal
rem This launcher changes environment variables only for this ZyntaxAI process.
rem Do not run the EXE directly; doing so would bypass ZYNTAX_DATA_DIR.
set "PORTABLE_ROOT=%~dp0"
set "ZYNTAX_DATA_DIR=%PORTABLE_ROOT%Data"
rem Official Microsoft Edge WebView2 environment override (process-local).
set "WEBVIEW2_USER_DATA_FOLDER=%PORTABLE_ROOT%Data\WebView2"
set "ZYNTAX_EXE=%PORTABLE_ROOT%App\zyntax.exe"
if not exist "%ZYNTAX_EXE%" (
    echo ERROR: App\zyntax.exe not found. Keep the portable folder intact.
    pause
    exit /b 1
)
if not exist "%ZYNTAX_DATA_DIR%" mkdir "%ZYNTAX_DATA_DIR%" 2>nul
if not exist "%ZYNTAX_DATA_DIR%" (
    echo ERROR: Cannot create the Data directory. Move this portable folder to a writable drive.
    pause
    exit /b 1
)
if not exist "%WEBVIEW2_USER_DATA_FOLDER%" mkdir "%WEBVIEW2_USER_DATA_FOLDER%" 2>nul
if not exist "%WEBVIEW2_USER_DATA_FOLDER%" (
    echo ERROR: Cannot create the WebView2 data directory.
    pause
    exit /b 1
)
start "" "%ZYNTAX_EXE%" %*
exit /b %errorlevel%
