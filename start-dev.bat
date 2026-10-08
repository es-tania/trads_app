@echo off
REM Lance tout le projet en un clic.

setlocal
set ROOT=%~dp0

echo === Services Docker (FlareSolverr + Redis) ===
pushd "%ROOT%backend"
docker compose up -d flaresolverr redis
popd

echo === Ouverture des fenetres (API / 3 Workers / Frontend) ===

start "API (uvicorn)" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

REM Deux workers "fast" : scraping et traduction peuvent tourner en meme temps.
start "Worker fast 1 (scraping/traduction)" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate.bat && python run_worker.py fast"
start "Worker fast 2 (scraping/traduction)" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate.bat && python run_worker.py fast"

REM UN SEUL worker "subtitles" : Whisper utilise le GPU, deux en parallele risquent de saturer la VRAM.
start "Worker subtitles (Whisper/GPU)" cmd /k "cd /d "%ROOT%backend" && call .venv\Scripts\activate.bat && python run_worker.py subtitles"

start "Frontend (Next.js)" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo.
echo Cinq fenetres viennent de s'ouvrir : API, 2 Workers fast, Worker subtitles, Frontend.
echo Ouverture du frontend dans le navigateur...

timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo Ferme-les (ou Ctrl+C dedans) pour tout arreter.
echo.
pause
