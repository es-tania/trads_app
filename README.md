# LADS App — traduction, OCR et sous-titres

Application web personnelle unifiant 4 outils auparavant séparés (n8n,
scripts en ligne de commande, GUI Tkinter) : scraping + traduction de
scripts de jeu, OCR d'images, traduction de documents Word, génération de
sous-titres synchronisés à partir de vidéos YouTube.

Voir [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) pour le schéma complet
et l'état d'avancement des phases.

## Lancer le projet

Après l'installation initiale (`backend/README.md` et `frontend/README.md` —
venv Python + `pip install`, `.env`, `npm install`), un seul script démarre
tout (Docker, API, worker, frontend) :

```bash
# Windows : double-clic sur start-dev.bat (ou start-dev.ps1 en PowerShell)
# macOS / Linux :
./start-dev.sh
```

Sous Windows, ça ouvre 3 fenêtres (API / Worker / Frontend) ; sous
macOS/Linux, les 3 tournent dans le même terminal avec des logs préfixés
(`[api]`, `[worker]`, `[frontend]`) — Ctrl+C arrête tout proprement.

Ça reste possible de lancer chaque brique à la main si besoin (voir
`backend/README.md`) :

```bash
cd backend && docker compose up -d flaresolverr redis
cd backend && uvicorn app.main:app --reload --port 8000
cd backend && python run_worker.py
cd frontend && npm run dev
```

## Structure

```
backend/
├── app/                 code de l'API (routes, services, jobs RQ)
├── legacy_scripts/      scripts d'origine réutilisés tels quels (module 03)
└── README.md            installation détaillée
frontend/                Interface Next.js (voir frontend/README.md)
docs/                    Documentation d'architecture et roadmap
```

## Statut

🚧 Phase 3 en cours — voir la checklist dans `docs/ARCHITECTURE.md`.
