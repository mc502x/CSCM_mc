<#
.SYNOPSIS  Runs one CSCM Tool CLI job (flask <command>) with the production configuration.
.EXAMPLE   run-job.ps1 -InstallDir C:\CSCM backup-db --keep 35
#>
param(
    [string]$InstallDir = "C:\CSCM",
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Command
)

$ErrorActionPreference = "Stop"
if (-not $Command) { throw "Give the flask command to run, e.g. backup-db" }
Set-Location (Join-Path $InstallDir "app")
& (Join-Path $InstallDir "venv\Scripts\flask.exe") --env-file (Join-Path $InstallDir "config\cscm.env") @Command
exit $LASTEXITCODE
