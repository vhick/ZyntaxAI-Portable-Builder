@echo off
setlocal EnableExtensions
title ZyntaxAI Portable Startup Setup

set "ROOT=%~dp0"
set "LAUNCHER=%ROOT%LAUNCH-ZYNTAXAI-PORTABLE.cmd"
set "DATADIR=%ROOT%Data"
set "VBS=%DATADIR%\Start-ZyntaxAI-Portable-Hidden.vbs"

if not exist "%DATADIR%" mkdir "%DATADIR%"

if not exist "%LAUNCHER%" (
  echo.
  echo ERROR: Portable launcher not found:
  echo   %LAUNCHER%
  echo.
  pause
  exit /b 1
)

rem The portable launcher itself always starts ZyntaxAI with --minimized.
rem The VBS wrapper only hides the temporary CMD window at Windows login.
> "%VBS%" echo Set sh = CreateObject("WScript.Shell")
>>"%VBS%" echo sh.CurrentDirectory = "%ROOT%"
>>"%VBS%" echo sh.Run Chr(34) ^& "%LAUNCHER%" ^& Chr(34), 0, False

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$startup=[Environment]::GetFolderPath('Startup');" ^
  "$lnk=Join-Path $startup 'ZyntaxAI-Portable.lnk';" ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$s=$w.CreateShortcut($lnk);" ^
  "$s.TargetPath=$env:WINDIR+'\System32\wscript.exe';" ^
  "$s.Arguments='\"%VBS%\"';" ^
  "$s.WorkingDirectory='%ROOT%';" ^
  "$s.Description='ZyntaxAI Portable - tray only';" ^
  "$s.Save();" ^
  "Write-Host ('Created/updated: '+$lnk)"

echo.
echo Portable startup is configured.
echo.
echo Both manual launch and Windows startup now begin in the system tray.
echo Open the ZyntaxAI GUI later from its tray icon.
echo.
echo Keep ZyntaxAI's built-in "Start with my computer" option OFF.
echo.
pause
