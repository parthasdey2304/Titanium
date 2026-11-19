@echo off
title Titanium AI Assistant (Console Mode)
cd /d "%~dp0"
echo ====================================================
echo           Starting Titanium Assistant...
echo ====================================================
call venv\Scripts\activate.bat
python.exe main.py
pause
