@echo off
rem Register this app in the "Open with" list for .md files (per-user, no admin).
rem
rem The exe is located relative to THIS script, so the folder can live anywhere:
rem Desktop, D:/Tools/MdReader, a USB stick ... no path is hard-coded.
setlocal
set "EXE=%~dp0MdReader.exe"

rem Fallback: older builds shipped a localized file name (e.g. "Markdown <cjk>.exe").
rem Match any exe whose name contains "Markdown" instead of hard-coding characters.
if not exist "%EXE%" (
  for /f "delims=" %%F in ('dir /b "%~dp0*Markdown*.exe" 2^>nul') do set "EXE=%~dp0%%F"
)

if not exist "%EXE%" (
  echo.
  echo [ERROR] MdReader.exe was not found next to this script:
  echo   %~dp0
  echo.
  echo Keep this .bat in the SAME folder as MdReader.exe and run it again.
  echo.
  pause
  exit /b 1
)

echo Registering: "%EXE%"
reg add "HKCU\Software\Classes\MarkdownReader.md" /ve /d "Markdown Document" /f >nul 2>&1
reg add "HKCU\Software\Classes\MarkdownReader.md\DefaultIcon" /ve /d "\"%EXE%\",0" /f >nul 2>&1
reg add "HKCU\Software\Classes\MarkdownReader.md\shell\open\command" /ve /d "\"%EXE%\" \"%%1\"" /f >nul 2>&1
reg add "HKCU\Software\Classes\.md\OpenWithProgids" /v MarkdownReader.md /t REG_NONE /d "" /f >nul 2>&1
reg add "HKCU\Software\Classes\.markdown\OpenWithProgids" /v MarkdownReader.md /t REG_NONE /d "" /f >nul 2>&1
reg add "HKCU\Software\Classes\.mdown\OpenWithProgids" /v MarkdownReader.md /t REG_NONE /d "" /f >nul 2>&1

if errorlevel 1 (
  echo.
  echo [ERROR] Failed to write to HKCU. Antivirus / group policy may have blocked it.
  echo.
  pause
  exit /b 1
)

echo.
echo Done. To make it the DEFAULT handler:
echo   1^) Right-click any .md file
echo   2^) Open with  ^>  Choose another app  ^>  "Markdown Document"
echo   3^) Tick "Always use this app"
echo.
echo No admin rights needed. To undo, delete HKCU\Software\Classes\MarkdownReader.md
echo.
pause
