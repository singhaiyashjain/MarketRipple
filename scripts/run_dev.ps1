# Windows helper: opens the backend and the frontend in two separate PowerShell windows.
# Usage (from the repo root):  powershell -ExecutionPolicy Bypass -File scripts\run_dev.ps1
$root = Split-Path -Parent $PSScriptRoot
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$root\backend'; if (-not (Test-Path .venv)) { python -m venv .venv; .venv\Scripts\activate; pip install -r requirements.txt } else { .venv\Scripts\activate }; uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$root\frontend'; if (-not (Test-Path node_modules)) { npm install }; npm run dev"
Write-Host "Backend: http://localhost:8000/docs   Frontend: http://localhost:5173"
