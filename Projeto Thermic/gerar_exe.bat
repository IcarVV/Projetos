@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% -m pip install -q flask openpyxl pyinstaller
%PY% -m PyInstaller --onefile --name Cronoanalise app.py
echo.
echo Pronto: copie dist\Cronoanalise.exe para a pasta do sistema,
echo junto com index.html, LogoThermic.png e LogoThermic.ico.
pause
