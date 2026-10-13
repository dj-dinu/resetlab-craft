@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" -B run_desktop.py
) else (
  py -3 -B run_desktop.py
)
