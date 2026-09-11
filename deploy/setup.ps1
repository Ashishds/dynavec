# Dynavec local setup script for Windows PowerShell
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      Dynavec Local Environment Setup    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 3 is required but was not found in PATH."
    exit 1
}
Write-Host "[OK] Detected Python: $pythonVersion" -ForegroundColor Green

# 2. Setup .env file
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[OK] Created .env from .env.example template." -ForegroundColor Green
        Write-Host "     Please edit .env with your AWS credentials and region." -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Existing .env file found." -ForegroundColor Green
}

# 3. Install dynavec in editable mode
Write-Host "`nInstalling dynavec and dependencies..." -ForegroundColor Cyan
pip install -e ".[all]"
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Installed dynavec successfully." -ForegroundColor Green
} else {
    Write-Warning "Failed installing full extras. Falling back to dev dependencies..."
    pip install -e ".[dev]"
}

# 4. Diagnostics check
Write-Host "`nRunning Dynavec diagnostics..." -ForegroundColor Cyan
python -m dynavec doctor

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Dynavec setup complete!" -ForegroundColor Green
Write-Host "To run tests:     pytest -q" -ForegroundColor White
Write-Host "To start dashboard: dynavec dashboard --port 8778" -ForegroundColor White
Write-Host "To run quickstart:  python examples/quickstart.py" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
