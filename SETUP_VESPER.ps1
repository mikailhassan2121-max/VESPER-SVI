$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed' }
& .\.venv\Scripts\python.exe -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
Write-Host 'Setup complete. Configure MASSIVE_API_KEY in .env, then run CHECK_VESPER.ps1.'
