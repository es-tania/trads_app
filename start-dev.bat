@echo off
REM Lance tout le projet en un clic : Redis/FlareSolverr (Docker), l'API,
REM le worker RQ et le frontend Next.js, chacun dans sa propre fenetre.
REM
REM Prerequis (une seule fois) :
REM   - backend\.venv cree et backend\requirements.txt installe
REM   - backend\.env rempli (voir backend\.env.example)
REM   - frontend : npm install
REM   - (optionnel) backend\deeplx-cli : npm install

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
echo Ferme-les (ou Ctrl+C dedans) pour tout arreter.
echo.
pause
