@echo off
title Install Titanium Assistant
cd /d "%~dp0"
echo ====================================================
echo        Installing Titanium into Windows...
echo ====================================================
call venv\Scripts\activate.bat
python.exe -c "from titanium.tools.installer import WindowsInstaller; res = WindowsInstaller.install(); print(res['message'])"
echo.
echo Titanium is now available in:
echo   1. Windows Start Menu (type 'Titanium')
echo   2. Windows Task Manager (Startup Apps tab)
echo   3. Desktop shortcut
echo.
pause
