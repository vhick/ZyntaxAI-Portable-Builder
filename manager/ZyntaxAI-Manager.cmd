@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "LAUNCHER=%~dp0ZyntaxAIPortable.exe"
set "STATUS=%~dp0Data\TraceGuard\ManagerStatus.txt"
set "REPORT=%~dp0Data\TraceGuard\Report.txt"
if not exist "%LAUNCHER%" (
  echo Missing ZyntaxAIPortable.exe in this directory.
  pause
  exit /b 1
)
:menu
cls
echo ZyntaxAI Native Portable Manager
echo.
echo 1 - Install/Repair Windows autostart, minimized to tray
echo 2 - Remove autostart
echo 3 - Autostart status
echo 4 - Launch normally
echo 5 - Launch minimized
echo 6 - Open portable Data folder
echo 7 - Run launcher self-test
echo 0 - Exit
echo.
set "CHOICE="
set /p "CHOICE=Selection: "
if "%CHOICE%"=="0" exit /b 0
if "%CHOICE%"=="1" (
  start "" /wait "%LAUNCHER%" --autostart-install
  goto status
)
if "%CHOICE%"=="2" (
  start "" /wait "%LAUNCHER%" --autostart-remove
  goto status
)
if "%CHOICE%"=="3" (
  start "" /wait "%LAUNCHER%" --autostart-status
  goto status
)
if "%CHOICE%"=="4" (
  start "" "%LAUNCHER%"
  goto menu
)
if "%CHOICE%"=="5" (
  start "" "%LAUNCHER%" --minimized
  goto menu
)
if "%CHOICE%"=="6" (
  start "" explorer.exe "%~dp0Data"
  goto menu
)
if "%CHOICE%"=="7" (
  start "" /wait "%LAUNCHER%" --self-test
  echo.
  if exist "%REPORT%" (type "%REPORT%") else (echo TraceGuard report was not created.)
  goto pausemenu
)
echo Choose a number from 0 through 7.
goto pausemenu
:status
echo.
if exist "%STATUS%" (type "%STATUS%") else (echo No manager status was created.)
:pausemenu
echo.
pause
goto menu
