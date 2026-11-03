@echo off
REM Desinstala Extractor de Metadatos de este equipo.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desinstalar.ps1"
if errorlevel 1 (
    echo.
    echo La desinstalacion no pudo completarse. Revisa el mensaje anterior.
)
echo.
pause
