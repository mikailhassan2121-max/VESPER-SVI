param([Parameter(Mandatory=$true)][string]$Dataset, [Parameter(Mandatory=$true)][string]$LockedStart)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& .\.venv\Scripts\python.exe -m vesper train --dataset $Dataset --locked-start $LockedStart
exit $LASTEXITCODE
