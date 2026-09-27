# LADS App — traduction, OCR et sous-titres

Application web personnelle unifiant 4 outils auparavant séparés (n8n,
scripts en ligne de commande, GUI Tkinter) : scraping + traduction de
scripts de jeu, OCR d'images, traduction de documents Word, génération de
sous-titres synchronisés à partir de vidéos YouTube.

Voir [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) pour le schéma complet
et l'état d'avancement des phases.

## Structure

```
backend/
├── app/                 code de l'API (routes, services)
├── legacy_scripts/      scripts d'origine réutilisés tels quels (module 03),
│                        seront progressivement portés en Phase 2
└── README.md            installation détaillée
frontend/                Interface Next.js (Phase 3, pas encore commencée)
docs/                    Documentation d'architecture et roadmap
```

## Statut

🚧 Phase 1 en cours — voir la checklist dans `docs/ARCHITECTURE.md`.
