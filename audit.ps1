# OMEGA package audit — double-click or run from Anti Gravity terminal
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"
python research/audit_package.py @args
exit $LASTEXITCODE
