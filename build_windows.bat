@echo off
REM ==========================================================================
REM  PC Repair Challenge - construir el ejecutable para Windows
REM
REM  Doble clic en este archivo dentro de una PC con Windows y con Python
REM  instalado. Genera dist\PCRepairChallenge.exe
REM ==========================================================================
setlocal
cd /d %~dp0

echo ==========================================
echo  PC Repair Challenge - empaquetar .exe
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro Python.
    echo Descargalo de https://www.python.org/downloads/
    echo Marca "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

if not exist ".venv_win" (
    echo [1/5] Creando entorno virtual ...
    python -m venv .venv_win
)
call .venv_win\Scripts\activate.bat

echo [2/5] Instalando dependencias ...
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet pyinstaller

echo [3/5] Generando el icono ...
python tools\make_icon.py

echo [4/5] Empaquetando (tarda unos minutos) ...
if exist build rd /s /q build
if exist dist rd /s /q dist
python -m PyInstaller --noconfirm --onefile --windowed --name PCRepairChallenge --add-data "assets\logos;assets/logos" --add-data "assets\icon.png;assets" --add-data "assets\fonts;assets/fonts" main.py
if errorlevel 1 (
    echo.
    echo [ERROR] El empaquetado fallo. Revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo.
echo [5/5] Listo.
echo.
echo    dist\PCRepairChallenge.exe
echo.
echo Copia ese archivo a cualquier PC con Windows de 64 bits y doble clic.
echo No necesita Python ni ningun otro programa instalado.
echo.
pause
