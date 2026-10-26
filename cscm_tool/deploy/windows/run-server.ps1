<#
.SYNOPSIS  Starts the CSCM Tool web server (Waitress). Registered by install.ps1 as a start-up task.
#>
param([string]$InstallDir = "C:\CSCM")

$ErrorActionPreference = "Stop"
$env:CSCM_ENV_FILE = Join-Path $InstallDir "config\cscm.env"
Set-Location (Join-Path $InstallDir "app")
& (Join-Path $InstallDir "venv\Scripts\python.exe") scripts\serve.py
exit $LASTEXITCODE
