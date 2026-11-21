@echo off
rem Sesli Yazma - sistem geneli dikteyi çalıştırır.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" sesli_yazma.py
) else (
    python sesli_yazma.py
)
if errorlevel 1 pause
