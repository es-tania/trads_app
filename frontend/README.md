# Frontend — Phase 3

Interface Next.js (App Router + TypeScript + Tailwind) pour les 3 modules
actifs du backend : scraping/traduction, traduction docx, sous-titres.
L'OCR reste désactivé côté UI tant que le backend n'est pas branché
(Phase 5).

## Installation

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Ouvre `http://localhost:3000`. Le backend (Phase 1+2) doit tourner en
parallèle sur `http://localhost:8000` (API + worker RQ + Redis +
FlareSolverr), sinon les formulaires échoueront.

## Choix de design

Thème sombre fixe (pas de bascule clair/sombre pour l'instant), pensé comme
une "salle de contrôle" : fond quasi-noir, un seul accent violet, statuts de
job codés par couleur (gris = en attente, violet = en cours, vert = terminé,
rouge = erreur). Les logs de chaque job s'affichent dans une console façon
terminal (police monospace), en direct via WebSocket.

## Structure

```
app/
├── layout.tsx        Layout racine (polices, sidebar)
├── page.tsx           Accueil
├── scraping/page.tsx  Scraper -> traduire -> générer les docx
├── translate/page.tsx Traduire un .docx uploadé
├── subtitles/page.tsx Générer des sous-titres (lien YouTube ou upload)
└── ocr/page.tsx       Placeholder (non branché)

components/
├── Sidebar.tsx         Navigation entre modules
├── JobStatusPanel.tsx  Panneau générique : statut + logs en direct + téléchargement
└── StatusPill.tsx      Pastille de statut colorée

lib/
├── api.ts     Appels au backend FastAPI
└── useJob.ts  Hook : suit un job (WebSocket logs + polling statut)
```

## Ce que je n'ai pas pu vérifier ici

Sans environnement Node.js/npm côté génération de ce projet, je n'ai pu
vérifier que la cohérence du code (imports, structure), pas le build réel
(`npm run build`) ni le rendu dans un navigateur. Fais-le tourner chez toi
et dis-moi si `npm install` ou `npm run dev` remontent une erreur.
