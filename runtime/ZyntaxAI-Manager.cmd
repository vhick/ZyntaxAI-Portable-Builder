@echo off
setlocal
:menu
cls
echo ===========================================================
echo  ZyntaxAI Native Portable Manager
echo ===========================================================
echo   1. Launch ZyntaxAI
echo   2. Open portable Data folder
echo   3. Open application logs
echo   4. Show portable paths and basic diagnostics
echo   0. Exit manager (does NOT stop ZyntaxAI)
echo.
choice /c 12340 /n /m "Choose: "
if errorlevel 5 exit /b 0
if errorlevel 4 goto diagnostics
if errorlevel 3 goto logs
if errorlevel 2 goto data
if errorlevel 1 goto launch
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
echo Window position persistence: Disabled to avoid profile writes
echo.
if exist "%~dp0App\zyntax.exe" (echo Application EXE found.) else (echo WARNING: Missing application EXE.)
reg query "HKLM\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F1E7E4F1-DA6C-4A73-9BC2-835921A027D6}" /v pv >nul 2>&1
if errorlevel 1 (echo WebView2 Runtime: Not confirmed by registry; application may still work if runtime is installed elsewhere.) else (echo WebView2 Runtime: Registry installation detected.)
echo.
echo No startup tasks, services, or registry entries are installed by this manager.
pause
goto menu
