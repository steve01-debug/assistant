@echo off
title Galadriel Background Launcher
cd /d "%~dp0"
start "" /b .venv\Scripts\pythonw.exe tray_app.py
exit
