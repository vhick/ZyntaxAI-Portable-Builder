@echo off
setlocal EnableExtensions
title ZyntaxAI Portable

set "ROOT=%~dp0"
set "EXE=%ROOT%ZyntaxAI-Portable.exe"
set "DATA=%ROOT%Data"
set "LOGDIR=%ROOT%LauncherLogs"
set "LOG=%LOGDIR%\Launch.log"

if not exist "%DATA%" mkdir "%DATA%" >nul 2>&1
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1

echo.>>"%LOG%"
echo ==== %date% %time% ZyntaxAI Portable launch ====>>"%LOG%"
echo EXE=%EXE%>>"%LOG%"
echo DATA=%DATA%>>"%LOG%"

if not exist "%EXE%" (
  echo ERROR: ZyntaxAI-Portable.exe not found.>>"%LOG%"
  echo ERROR: ZyntaxAI-Portable.exe was not found.
  pause
  exit /b 1
)

start "" "%EXE%"
exit /b 0
