@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Instalar Dicto

echo.
echo   Dicto · instalación
echo   ───────────────────
echo.

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo   No se ha encontrado Python.
    echo   Instálalo desde https://www.python.org/downloads/ marcando "Add python.exe to PATH"
    echo   y vuelve a ejecutar este instalador.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo   [1/3] Creando el entorno de Python...
    %PY% -m venv .venv || goto :error
) else (
    echo   [1/3] Entorno de Python ya creado.
)

echo   [2/3] Instalando dependencias. Puede tardar unos minutos...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check
where nvidia-smi >nul 2>&1
if %errorlevel%==0 (
    echo         GPU NVIDIA detectada: se instala el soporte CUDA.
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check || goto :error
) else (
    echo         Sin GPU NVIDIA: Dicto funcionará en CPU.
    findstr /v /i "nvidia" requirements.txt > "%TEMP%\dicto-requirements.txt"
    ".venv\Scripts\python.exe" -m pip install -r "%TEMP%\dicto-requirements.txt" --disable-pip-version-check || goto :error
    del "%TEMP%\dicto-requirements.txt" >nul 2>&1
)

echo   [3/3] Abriendo Dicto...
echo.
echo   La primera vez se descarga el modelo de voz (~1,6 GB con el modelo Turbo).
echo   Mientras tanto el icono de la bandeja se verá gris. Cuando se ponga azul, ya puedes dictar.
echo.
start "" ".venv\Scripts\pythonw.exe" dicto.py
echo   Listo. A partir de ahora abre Dicto desde el menú Inicio o el escritorio.
echo.
pause
exit /b 0

:error
echo.
echo   Algo ha fallado durante la instalación. Revisa los mensajes de arriba.
echo.
pause
exit /b 1
