# Lance tout le projet en un clic : Redis/FlareSolverr (Docker), l'API,
# le worker RQ et le frontend Next.js, chacun dans sa propre fenetre.
#
# Usage : clic droit -> "Exécuter avec PowerShell", ou :
#   powershell -ExecutionPolicy Bypass -File .\start-dev.ps1
#
# Prerequis (une seule fois) : voir start-dev.bat

$root = $PSScriptRoot

Write-Host "=== Services Docker (FlareSolverr + Redis) ===" -ForegroundColor Cyan
Push-Location "$root\backend"
docker compose up -d flaresolverr redis
Pop-Location

Write-Host "=== Ouverture des 3 fenetres (API / Worker / Frontend) ===" -ForegroundColor Cyan

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000"
) -WindowStyle Normal

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\backend'; .\.venv\Scripts\Activate.ps1; python run_worker.py"
) -WindowStyle Normal

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\frontend'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "Trois fenetres viennent de s'ouvrir : API, Worker, Frontend." -ForegroundColor Green
Write-Host "Ferme-les (ou Ctrl+C dedans) pour tout arreter."
