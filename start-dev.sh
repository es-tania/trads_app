#!/usr/bin/env bash
# Lance tout le projet en une commande : Redis/FlareSolverr (Docker), l'API,
# le worker RQ et le frontend Next.js, avec logs préfixés dans un seul
# terminal. Ctrl+C arrête tout proprement.
#
# Prérequis (une seule fois) :
#   - backend/.venv créé et backend/requirements.txt installé
#   - backend/.env rempli (voir backend/.env.example)
#   - frontend : npm install
#   - (optionnel) backend/deeplx-cli : npm install

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "=== Services Docker (FlareSolverr + Redis) ==="
(cd backend && docker compose up -d flaresolverr redis) || echo "⚠️  Docker indisponible, étape ignorée."

pids=()

cleanup() {
    echo ""
    echo "Arrêt des services..."
    for pid in "${pids[@]}"; do
        kill "$pid" 2>/dev/null
    done
    wait 2>/dev/null
}
trap cleanup EXIT INT TERM

echo "=== Lancement de l'API, du worker et du frontend ==="

(
    cd backend
    source .venv/bin/activate
    exec uvicorn app.main:app --reload --port 8000
) 2>&1 | sed -u "s/^/[api] /" &
pids+=($!)

(
    cd backend
    source .venv/bin/activate
    exec python run_worker.py
) 2>&1 | sed -u "s/^/[worker] /" &
pids+=($!)

(
    cd frontend
    exec npm run dev
) 2>&1 | sed -u "s/^/[frontend] /" &
pids+=($!)

wait
