@echo off
title Titanium AI Assistant
cd /d "%~dp0"
if exist venv\Scripts\pythonw.exe (
    start "" "venv\Scripts\pythonw.exe" main.py
) else (
    pythonw main.py
)
exit
