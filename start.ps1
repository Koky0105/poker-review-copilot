$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Python environment setup failed" }
}
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed" }
npm --prefix frontend ci
if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed" }
npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
Write-Host "Open http://127.0.0.1:8000 in your browser. Ctrl+C stops the server."
& .\.venv\Scripts\python.exe -m uvicorn poker_review.api:create_app --factory --host 127.0.0.1 --port 8000
