@echo off
setlocal
cd /d "%~dp0"

py -3 -m pip install --upgrade pip
if errorlevel 1 exit /b 1

py -3 -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

py -3 -m unittest discover -s tests -v
if errorlevel 1 exit /b 1

py -3 -m PyInstaller --noconfirm --clean --windowed --onedir --name ESP32-Data-Monitor --collect-all pyqtgraph --hidden-import serial.tools.list_ports --paths . app\main.py
if errorlevel 1 exit /b 1

set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Nie znaleziono Inno Setup 6. Zainstaluj Inno Setup i uruchom ponownie.
  exit /b 1
)

"%ISCC%" installer\setup.iss
if errorlevel 1 exit /b 1

echo Gotowy instalator: installer\Output\ESP32-Data-Monitor-Setup.exe
