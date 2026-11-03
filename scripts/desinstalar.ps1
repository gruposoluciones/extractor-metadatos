<#
.SYNOPSIS
    Desinstala Extractor de Metadatos del perfil del usuario.
.DESCRIPTION
    Cierra la aplicación si está en ejecución, elimina los accesos directos y
    borra la carpeta de instalación. No toca los documentos analizados.
#>
param(
    [string]$Destino = (Join-Path $env:LOCALAPPDATA "DIVIAC\ExtractorMetadatos")
)

$ErrorActionPreference = "Stop"

Get-Process ExtractorMetadatos -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 400

$accesos = @(
    (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Extractor de Metadatos.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Extractor de Metadatos.lnk")
)
foreach ($ruta in $accesos) {
    if (Test-Path $ruta) { Remove-Item $ruta -Force }
}

if (Test-Path $Destino) { Remove-Item $Destino -Recurse -Force }

Write-Host "Desinstalación completada." -ForegroundColor Green
