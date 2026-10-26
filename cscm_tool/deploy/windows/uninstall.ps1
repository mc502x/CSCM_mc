<#
.SYNOPSIS  Removes the CSCM Tool scheduled tasks. Never deletes data, configuration or backups.
.DESCRIPTION
  The application files, the database (data\), the configuration (config\) and the backups
  (backups\) stay where they are; delete the install directory by hand when you are certain
  they are no longer needed (the audit log has a 7-year retention requirement, docs/12).
#>
[CmdletBinding()]
param([switch]$DryRun)

$names = "CSCM Tool - web server", "CSCM Tool - nightly backup", "CSCM Tool - reminders", "CSCM Tool - audit chain check"
foreach ($name in $names) {
    if ($DryRun) { Write-Host "    [dry-run] unregister '$name'"; continue }
    Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "removed '$name'"
}
Write-Host "Data, configuration and backups were left in place."
