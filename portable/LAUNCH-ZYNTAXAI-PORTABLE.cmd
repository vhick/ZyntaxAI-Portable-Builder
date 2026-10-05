@echo off
setlocal EnableExtensions
title ZyntaxAI Portable

set "ROOT=%~dp0"
set "EXE=%ROOT%ZyntaxAI-Portable.exe"
set "DATA=%ROOT%Data"
set "ZYNTAX_DATA_DIR=%ROOT%Data\ZyntaxStore"
set "LOGDIR=%ROOT%LauncherLogs"
set "LOG=%LOGDIR%\Launch.log"

if not exist "%DATA%" mkdir "%DATA%" >nul 2>&1
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1

echo.>>"%LOG%"
echo ==== %date% %time% ZyntaxAI Portable launch ====>>"%LOG%"
echo EXE=%EXE%>>"%LOG%"
echo DATA=%DATA%>>"%LOG%"
echo ZYNTAX_DATA_DIR=%ZYNTAX_DATA_DIR%>>"%LOG%"
echo Mode=tray-only (--minimized)>>"%LOG%"

if not exist "%EXE%" (
  echo ERROR: ZyntaxAI-Portable.exe not found.>>"%LOG%"
  echo.
  echo ERROR: ZyntaxAI-Portable.exe was not found beside this launcher.
  echo.
  pause
  exit /b 1
)

rem Always launch ZyntaxAI hidden in the system tray.
rem Open the GUI later from the ZyntaxAI tray icon.
start "" "%EXE%" --minimized
exit /b 0
