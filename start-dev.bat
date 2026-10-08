@echo off
REM Lance tout le projet en un clic.

setlocal
set ROOT=%~dp0

echo === Services Docker (FlareSolverr + Redis) ===
pushd "%ROOT%backend"
docker compose up -d flaresolverr redis
popd

echo === Ouverture des 3 fenetres (API / Worker / Frontend) ===

start "API (uvicorn)" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

start "Worker (RQ)" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate.bat && python run_worker.py"

start "Frontend (Next.js)" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo.
echo Trois fenetres viennent de s'ouvrir : API, Worker, Frontend.
echo Ouverture du frontend dans le navigateur...

timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo Ferme-les (ou Ctrl+C dedans) pour tout arreter.
echo.
pause