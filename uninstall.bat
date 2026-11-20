@echo off
title Titanium - Disable System Integration
echo ========================================================
echo   Titanium AI Assistant - Unregister System Integration
echo ========================================================
echo.
echo Disabling Windows Start Menu, Desktop shortcuts, and Task Manager Startup...
echo NOTE: Your project files, virtual environment, and source code will NOT be touched.
echo.

python -c "from titanium.tools.installer import WindowsInstaller; res = WindowsInstaller.uninstall(); print('Status:', res.get('message'))"

echo.
echo [Done] Titanium system integration removed successfully.
pause
