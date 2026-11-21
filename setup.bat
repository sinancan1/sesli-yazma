@echo off
rem Sesden Yazıya - kurulum betiği: sanal ortam oluşturup bağımlılıkları kurar.
cd /d "%~dp0"
python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Kurulum bitti. Programi baslatmak icin start.bat dosyasini kullanin.
pause
