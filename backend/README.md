# Backend unifié — Phase 1 + 2

Fusionne les 4 modules derrière une seule API FastAPI, sans n8n et sans
Node.js (Phase 1), avec les tâches longues (scraping, traduction,
sous-titres) exécutées en file d'attente Redis/RQ plutôt que de bloquer la
requête HTTP (Phase 2).

## Ce qui a changé par rapport aux scripts d'origine

- **Traduction** : deux moteurs au choix (paramètre `engine`, ou
  `TRANSLATE_ENGINE` dans `.env`) :
  - `deepl` : API DeepL officielle (`deepl` SDK Python, palier gratuit
    500 000 caractères/mois, clé requise).
  - `deeplx` : CLI Node.js `deeplx` (gratuit, sans clé) — le même outil que
    l'ancien module 02, mais appelé proprement depuis Python (plus de
    fichiers temporaires ni de `shell=True`). Nécessite `npm install` dans
    `deeplx-cli/` une fois (voir ci-dessous).
  Utilisée à la fois par `/scraping/translate` et `/translate/docx`.
- **Génération du docx du script scrapé** : le script Node.js
  `generate_script_docx.js` a été porté en Python pur
  (`app/services/script_docx_generator.py`) — plus besoin de Node.js du tout.
- **Extraction texte des .docx** : faite avec `python-docx` directement
  (`app/services/docx_utils.py`) — **pandoc n'est plus nécessaire**.
- **Chemins en dur** (`C:\Users\tanes\...`) → tout passe par `STORAGE_DIR`
  dans `.env`, portable sur n'importe quelle machine.
- **OCR image (module 01)** : volontairement laissé en stub
  (`app/routers/ocr.py`) — à brancher une fois que tu as testé un modèle de
  vision local (Ollama) sur tes images.
- **Sous-titres (module 03)** : `yt-dlp` ajouté pour télécharger directement
  depuis un lien YouTube ; tes scripts `1_align.py`, `1_fr_txt_to_segments.py`,
  `2_merge_to_srt.py`, `4_fix_srt_timings.py` sont réutilisés tels quels via
  subprocess (pas réécrits, pour ne pas risquer de casser la logique Whisper).
  Ils vivent maintenant dans `legacy_scripts/subtitles/` (à l'intérieur de
  `backend/`) — plus de dossier externe à maintenir à côté du repo.

## Installation

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate sous Windows
pip install -r requirements.txt

cp .env.example .env
# édite .env et renseigne DEEPL_API_KEY (clé gratuite sur deepl.com/pro-api)
# -- uniquement si tu comptes utiliser le moteur "deepl". Pour "deeplx" (gratuit,
# sans clé), rien à mettre dans .env, mais il faut installer son CLI Node.js :
cd deeplx-cli && npm install && cd ..
```

Il te faut Node.js installé et dans le PATH pour le moteur `deeplx` (CLI
appelé via `node`, voir `app/services/deeplx_translate.py`).

Il te faut aussi `ffmpeg` installé et dans le PATH (nécessaire à Whisper) :
- Windows : https://ffmpeg.org/download.html
- macOS : `brew install ffmpeg`
- Linux : `sudo apt install ffmpeg`

## Lancer les services annexes (FlareSolverr + Redis)

```bash
docker compose up -d flaresolverr redis
```

## Lancer l'API (terminal 1)

```bash
uvicorn app.main:app --reload --port 8000
```

## Lancer le worker (terminal 2) — nouveau en Phase 2

`/scraping/scrape`, `/scraping/translate`, `/translate/docx` et
`/subtitles/generate` ne font plus le travail dans la requête HTTP : elles
mettent un job en file d'attente et répondent tout de suite. Il faut donc un
**worker** qui tourne en parallèle pour exécuter ces jobs :

```bash
python run_worker.py
```

⚠️ Ne pas utiliser la commande `rq worker` standard : elle repose sur
`os.fork()`, indisponible sur Windows. `run_worker.py` utilise `SimpleWorker`
à la place, qui fonctionne identiquement sur toutes les plateformes (voir le
commentaire en tête de ce fichier pour le détail du compromis).

Sans ce worker lancé, les jobs restent bloqués en statut `queued` pour
toujours.

Documentation interactive de l'API : http://localhost:8000/docs

## Nouveau flux asynchrone (scraping, traduction, sous-titres)

Même principe pour `/scraping/scrape`, `/scraping/translate`,
`/translate/docx` et `/subtitles/generate` :

1. La route répond immédiatement avec `{"job_id": "..."}` (code 202)
2. `GET /jobs/{job_id}` → statut courant (`queued` / `running` / `done` / `error`) + historique des logs
3. `GET /jobs/{job_id}/result` → télécharge le fichier produit une fois `status = done`
4. WebSocket `/jobs/{job_id}/ws` → journal en direct (équivalent au log de
   ta GUI Tkinter), se ferme automatiquement à la fin du job

`/scraping/generate-docx` reste synchrone (traitement local, quasi
instantané, pas besoin de file d'attente).

## Pourquoi le backend ne tourne pas encore dans Docker

Pour garder un accès natif et simple à ton GPU (Whisper), le backend et le
worker tournent directement sur ta machine (venv) plutôt que dans un
conteneur — la conteneurisation complète avec accès GPU (nvidia-docker)
n'est pas nécessaire pour un usage solo et ajouterait de la complexité pour
peu de bénéfice ici.

## Prochaines étapes (Phase 3)

1. Brancher l'OCR (`app/routers/ocr.py`) une fois le modèle de vision choisi
   — sur le même modèle jobs asynchrones que les sous-titres.
2. Construire le frontend Next.js qui appelle ces routes (formulaires,
   suivi de statut, logs en direct via la WebSocket).
