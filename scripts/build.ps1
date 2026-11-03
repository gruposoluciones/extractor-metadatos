<#
.SYNOPSIS
    Compila el ejecutable de Windows delegando en build.py.
.DESCRIPTION
    Envoltorio de PowerShell sobre build.py, el orquestador multiplataforma.
    En macOS se usa el mismo build.py a través de build.sh.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\build.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\build.ps1 -OneFile
#>
param(
    [switch]$OneFile,
    [switch]$Check,
    [switch]$Install
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$argumentos = @()
if ($OneFile) { $argumentos += "--onefile" }
if ($Check) { $argumentos += "--check" }
if ($Install) { $argumentos += "--install" }

python build.py @argumentos
exit $LASTEXITCODE
