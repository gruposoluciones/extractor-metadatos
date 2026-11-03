@echo off
REM Instala Extractor de Metadatos en este equipo (sin permisos de administrador).
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
if errorlevel 1 (
    echo.
    echo La instalacion no pudo completarse. Revisa el mensaje anterior.
)
echo.
pause
