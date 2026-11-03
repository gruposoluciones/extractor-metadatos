<#
.SYNOPSIS
    Instala Extractor de Metadatos en el perfil del usuario, sin permisos de administrador.
.DESCRIPTION
    Copia la aplicación a %LOCALAPPDATA%\DIVIAC\ExtractorMetadatos y crea accesos
    directos en el menú Inicio y en el escritorio. Funciona sobre la salida de
    scripts\build.py, sobre un ZIP portable o desde la raíz del proyecto.
.PARAMETER Destino
    Carpeta de instalación. Por omisión %LOCALAPPDATA%\DIVIAC\ExtractorMetadatos.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\instalar.ps1
#>
param(
    [string]$Destino = (Join-Path $env:LOCALAPPDATA "DIVIAC\ExtractorMetadatos")
)

$ErrorActionPreference = "Stop"

$candidatos = @(
    $PSScriptRoot,
    (Join-Path $PSScriptRoot "..\dist\ExtractorMetadatos"),
    (Join-Path $PSScriptRoot "dist\ExtractorMetadatos")
)
$Origen = $null
foreach ($candidato in $candidatos) {
    if (Test-Path (Join-Path $candidato "ExtractorMetadatos.exe")) {
        $Origen = (Resolve-Path $candidato).Path
        break
    }
}
if (-not $Origen) {
    throw "No se encontró ExtractorMetadatos.exe. Ejecuta antes: python scripts\build.py"
}

Write-Host "Instalando desde: $Origen" -ForegroundColor Cyan

$origenReal = (Resolve-Path $Origen).Path.TrimEnd('\')
$destinoReal = $Destino.TrimEnd('\')
if ($origenReal -eq $destinoReal) {
    Write-Host "La aplicación ya está instalada en esa carpeta." -ForegroundColor Yellow
    exit 0
}

Get-Process ExtractorMetadatos -ErrorAction SilentlyContinue | Stop-Process -Force
if (Test-Path $Destino) { Remove-Item $Destino -Recurse -Force }
New-Item -ItemType Directory -Path $Destino -Force | Out-Null
Copy-Item (Join-Path $Origen "*") $Destino -Recurse -Force

$exe = Join-Path $Destino "ExtractorMetadatos.exe"
$shell = New-Object -ComObject WScript.Shell

$accesos = @(
    (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Extractor de Metadatos.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Extractor de Metadatos.lnk")
)
foreach ($ruta in $accesos) {
    $acceso = $shell.CreateShortcut($ruta)
    $acceso.TargetPath = $exe
    $acceso.WorkingDirectory = $Destino
    $acceso.IconLocation = "$exe,0"
    $acceso.Description = "Extractor de Metadatos - DIVIAC"
    $acceso.Save()
}

Write-Host ""
Write-Host "Instalado en: $Destino" -ForegroundColor Green
Write-Host "Accesos directos creados en el menú Inicio y en el escritorio." -ForegroundColor Green
Write-Host "Abre 'Extractor de Metadatos' y el navegador mostrará la interfaz." -ForegroundColor Green
