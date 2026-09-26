# Backend unifié — Phase 1

Fusionne les 4 modules derrière une seule API FastAPI, sans n8n et sans
Node.js. Rien n'est encore mis en file d'attente (jobs synchrones pour
l'instant) — c'est l'objectif de la Phase 2.

## Ce qui a changé par rapport aux scripts d'origine

- **Traduction** : `deeplx` (Node.js, non officiel) → API DeepL officielle
  (`deepl` SDK Python, palier gratuit 500 000 caractères/mois). Utilisée à la
  fois par `/scraping/translate` et `/translate/docx`.
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

## Installation

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate sous Windows
pip install -r requirements.txt

cp .env.example .env
# édite .env et renseigne DEEPL_API_KEY (clé gratuite sur deepl.com/pro-api)
```

Il te faut aussi `ffmpeg` installé et dans le PATH (nécessaire à Whisper) :
- Windows : https://ffmpeg.org/download.html
- macOS : `brew install ffmpeg`
- Linux : `sudo apt install ffmpeg`

## Lancer FlareSolverr (nécessaire pour le scraping)

```bash
docker compose up -d flaresolverr
```

## Lancer l'API

```bash
uvicorn app.main:app --reload --port 8000
```

Documentation interactive (pour tester chaque route sans frontend) :
http://localhost:8000/docs

## Pourquoi le backend ne tourne pas encore dans Docker

Pour garder un accès natif et simple à ton GPU (Whisper), on lance le
backend directement sur ta machine (venv) pour l'instant plutôt que dans un
conteneur — la conteneurisation complète avec accès GPU (nvidia-docker) sera
traitée en Phase 2, en même temps que la file d'attente Redis/RQ.

## Prochaines étapes (Phase 2)

1. Ajouter Redis + RQ : chaque route ci-dessus devient un job asynchrone au
   lieu de bloquer la requête HTTP (important pour `/subtitles/generate`,
   qui peut prendre plusieurs minutes).
2. Ajouter une WebSocket par job pour streamer les logs en direct (comme ta
   GUI Tkinter actuelle).
3. Brancher l'OCR (`app/routers/ocr.py`) une fois le modèle de vision choisi.
4. Construire le frontend Next.js qui appelle ces routes.
