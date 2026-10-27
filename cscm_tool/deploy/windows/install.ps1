<#
.SYNOPSIS
  CSCM Tool - on-premises installer for Windows Server. docs/14-deployment-architecture.md section 4.

.DESCRIPTION
  Installs or upgrades from this checkout: code, virtual environment, configuration (once),
  database migrations, the first Administrator, and the scheduled tasks (web server at start-up,
  nightly verified backup, weekday reminders, weekly audit-chain check).

  Idempotent: running it again upgrades the code and applies pending migrations and leaves the
  configuration, the database and the backups alone. The only network access is pip installing
  requirements.txt - set PIP_INDEX_URL to your internal mirror when the server has no internet.

.PARAMETER InstallDir   Where the application goes (default C:\CSCM).
.PARAMETER RunAs        Account the tasks run under (default SYSTEM). A dedicated service account
                        with write access to the InstallDir is better practice.
.PARAMETER Python       Python 3.12+ interpreter to build the environment with (default "python").
.PARAMETER DryRun       Print every step, change nothing.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File deploy\windows\install.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$InstallDir = "C:\CSCM",
    [string]$RunAs = "SYSTEM",
    [string]$Python = "python",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Source = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$App = Join-Path $InstallDir "app"
$Venv = Join-Path $InstallDir "venv"
$Config = Join-Path $InstallDir "config"
$EnvFile = Join-Path $Config "cscm.env"
$Data = Join-Path $InstallDir "data"
$Backups = Join-Path $InstallDir "backups"
$Logs = Join-Path $InstallDir "logs"

function Step([string]$Text) { Write-Host "==> $Text" }
function Invoke-Step([string]$Description, [scriptblock]$Action) {
    if ($DryRun) { Write-Host "    [dry-run] $Description" } else { & $Action }
}
function New-Secret { -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ }) }

if (-not (Test-Path (Join-Path $Source "wsgi.py"))) { throw "Run this from a CSCM checkout: $Source\wsgi.py not found." }
if (-not $DryRun) {
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run from an elevated PowerShell, or use -DryRun."
    }
}
$version = & $Python -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$version -lt [version]"3.12") { throw "Python 3.12 or newer is required (found $version)." }

Step "Directories under $InstallDir"
foreach ($dir in @($App, $Config, $Data, "$Data\instance", $Backups, $Logs)) {
    Invoke-Step "create $dir" { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
}

Step "Application code -> $App"
Invoke-Step "copy app, migrations, scripts, wsgi.py, requirements.txt" {
    foreach ($item in "app", "migrations", "scripts", "deploy") {
        Copy-Item -Recurse -Force (Join-Path $Source $item) $App
    }
    foreach ($file in "wsgi.py", "requirements.txt", "pyproject.toml") {
        Copy-Item -Force (Join-Path $Source $file) $App
    }
    # The baseline migration executes docs\artifacts\schema.sql, found two levels above its own folder.
    New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "docs\artifacts") | Out-Null
    foreach ($sql in "schema.sql", "schema-fts5.sql") {
        Copy-Item -Force (Join-Path $Source "..\docs\artifacts\$sql") (Join-Path $InstallDir "docs\artifacts")
    }
}

Step "Virtual environment -> $Venv"
Invoke-Step "python -m venv $Venv; pip install runtime requirements" {
    if (-not (Test-Path $Venv)) { & $Python -m venv $Venv }
    # everything before the "# --- dev" marker is the runtime set
    $lines = Get-Content (Join-Path $Source "requirements.txt")
    $stop = ($lines | Select-String -Pattern "^# --- dev" | Select-Object -First 1).LineNumber
    $runtime = if ($stop) { $lines[0..($stop - 2)] } else { $lines }
    $tmp = Join-Path $env:TEMP "cscm-runtime-requirements.txt"
    $runtime | Set-Content -Encoding ascii $tmp
    & "$Venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    & "$Venv\Scripts\python.exe" -m pip install --quiet -r $tmp
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
}

Step "Configuration -> $EnvFile"
if (Test-Path $EnvFile) {
    Write-Host "    exists - left untouched"
} else {
    Invoke-Step "create $EnvFile with generated SECRET_KEY, AUDIT_HMAC_KEY, MANIFEST_SIGNING_KEY (access limited to Administrators and $RunAs)" {
        $dataUri = ($Data -replace "\\", "/")
        @(
            "FLASK_APP=wsgi.py",
            "FLASK_ENV=production",
            "SECRET_KEY=$(New-Secret)",
            "AUDIT_HMAC_KEY=$(New-Secret)",
            "MANIFEST_SIGNING_KEY=$(New-Secret)",
            "DATABASE_URL=sqlite:///$dataUri/cscm.db",
            "CSCM_INSTANCE_PATH=$Data\instance",
            "BACKUP_DIR=$Backups",
            "LOG_FILE=$Logs\cscm.log",
            "CSCM_HOST=127.0.0.1",
            "CSCM_PORT=8000",
            "CSCM_ENV_FILE=$EnvFile"
        ) | Set-Content -Encoding ascii $EnvFile
        icacls $EnvFile /inheritance:r /grant:r "Administrators:(F)" "${RunAs}:(R)" | Out-Null
        Write-Host "    created. Keep a copy of the three keys in the password safe: they cannot be recovered."
    }
}

function Invoke-Flask([string[]]$FlaskArgs) {
    Push-Location $App
    try { & "$Venv\Scripts\flask.exe" --env-file $EnvFile @FlaskArgs; if ($LASTEXITCODE -ne 0) { throw "flask $($FlaskArgs -join ' ') failed" } }
    finally { Pop-Location }
}

Step "Database migrations"
Invoke-Step "flask db upgrade (a backup of an existing database is taken first)" {
    if (Test-Path "$Data\cscm.db") {
        try { Invoke-Flask @("backup-db") } catch { Write-Warning "pre-upgrade backup failed: $_" }
    }
    Invoke-Flask @("db", "upgrade")
    # the initial legacy -> new mapping, only into an empty table (FR-191)
    try { Invoke-Flask @("mapping-seed") } catch { Write-Warning "the mapping was not loaded; an Administrator can load it from the Mapping page: $_" }
    # tell the StCd Owner what this version changed in the interface text or the nomenclature (FR-178)
    try { Invoke-Flask @("translation-impact") } catch { Write-Warning "translation-impact failed: $_" }
}

Step "First Administrator"
Invoke-Step "flask create-admin (only if the database has no users)" {
    $count = & "$Venv\Scripts\python.exe" -c "import sqlite3; print(sqlite3.connect(r'$Data\cscm.db').execute('select count(*) from user').fetchone()[0])"
    if ($count -eq "0") {
        Write-Host "    No users yet. Choose the administrator account:"
        Invoke-Flask @("create-admin")
    } else { Write-Host "    users exist - skipped" }
}

Step "Scheduled tasks"
$job = Join-Path $App "deploy\windows\run-job.ps1"
$server = Join-Path $App "deploy\windows\run-server.ps1"
$ps = "powershell.exe"
$common = "-NoProfile -ExecutionPolicy Bypass -File"
$tasks = @(
    @{ Name = "CSCM Tool - web server"; Args = "$common `"$server`" -InstallDir `"$InstallDir`""; Trigger = (New-ScheduledTaskTrigger -AtStartup); Long = $true },
    @{ Name = "CSCM Tool - nightly backup"; Args = "$common `"$job`" -InstallDir `"$InstallDir`" backup-db --keep 35"; Trigger = (New-ScheduledTaskTrigger -Daily -At 2:15am) },
    @{ Name = "CSCM Tool - reminders"; Args = "$common `"$job`" -InstallDir `"$InstallDir`" send-reminders"; Trigger = (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 7:30am) },
    @{ Name = "CSCM Tool - audit chain check"; Args = "$common `"$job`" -InstallDir `"$InstallDir`" audit-verify"; Trigger = (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3:30am) }
)
foreach ($task in $tasks) {
    Invoke-Step "register '$($task.Name)'" {
        $action = New-ScheduledTaskAction -Execute $ps -Argument $task.Args -WorkingDirectory $App
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
        if ($task.Long) { $settings.ExecutionTimeLimit = "PT0S" }
        Register-ScheduledTask -Force -TaskName $task.Name -Action $action -Trigger $task.Trigger `
            -Settings $settings -User $RunAs -RunLevel Highest | Out-Null
    }
}
Invoke-Step "start 'CSCM Tool - web server'" {
    Stop-ScheduledTask -TaskName "CSCM Tool - web server" -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName "CSCM Tool - web server"
}

Step "Done"
Write-Host "    Application: http://127.0.0.1:8000  (terminate TLS in IIS/ARR or nginx in front of it)"
Write-Host "    Check:       Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready"
