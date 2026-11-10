"""
Remplace le module 00 (n8n) : scraper une page de script, générer le docx EN,
traduire, générer le docx FR. Tout dans l'API, sans n8n.

Le scraping (dépend de FlareSolverr, peut être lent sur Cloudflare) et la
traduction (DeepL ou DeepLX) passent par la file d'attente "fast" — suivre
l'avancement via GET /jobs/{job_id} ou WS /jobs/{job_id}/ws. La génération
du docx reste synchrone : c'est purement local et quasi instantané.
"""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.jobs.queue import queue_fast
from app.jobs.tasks import task_scrape, task_translate_scraped
from app.services.script_docx_generator import generate_docx
from app.services.translation import ENGINES

router = APIRouter(prefix="/scraping", tags=["scraping"])

SCRIPTS_DIR = settings.storage_dir / "scripts"


class ScrapeRequest(BaseModel):
    url: str


class GenerateDocxRequest(BaseModel):
    folder: str
    filename: str
    lang: str = "EN"


class TranslateRequest(BaseModel):
    folder: str
    filename: str
    engine: str | None = None  # "deepl" ou "deeplx" ; défaut = TRANSLATE_ENGINE (.env)


@router.post("/scrape", status_code=202)
def scrape(payload: ScrapeRequest):
    """Met en file d'attente la récupération d'un script (remplace le scraping n8n)."""
    job_id = uuid.uuid4().hex
    queue_fast.enqueue(task_scrape, job_id, payload.url, job_id=job_id, job_timeout="5m")
    return {"job_id": job_id}


@router.post("/generate-docx")
def generate_docx_route(payload: GenerateDocxRequest):
    """Génère le .docx (EN ou FR) depuis le JSON scrapé — plus de dépendance Node.js."""
    json_path = SCRIPTS_DIR / payload.folder / payload.filename
    if not json_path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {json_path}")

    output_path = SCRIPTS_DIR / payload.folder / f"{payload.lang}.docx"
    generate_docx(json_path, output_path)
    return {"folder": payload.folder, "file": output_path.name}


@router.get("/download")
def download_scraped_file(folder: str, filename: str):
    """Télécharge un fichier du dossier d'un script scrapé (json ou docx)."""
    if "/" in folder or "\\" in folder or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nom de fichier ou dossier invalide")

    path = SCRIPTS_DIR / folder / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {path}")

    return FileResponse(path, filename=filename)


@router.post("/translate", status_code=202)
def translate_scraped_script(payload: TranslateRequest):
    """Met en file d'attente la traduction du script scrapé (DeepL ou DeepLX local)."""
    json_path = SCRIPTS_DIR / payload.folder / payload.filename
    if not json_path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {json_path}")

    if payload.engine is not None and payload.engine.lower() not in ENGINES:
        raise HTTPException(
            status_code=400, detail=f"Moteur inconnu : {payload.engine!r} (attendu : {sorted(ENGINES)})"
        )

    job_id = uuid.uuid4().hex
    queue_fast.enqueue(
        task_translate_scraped, job_id, payload.folder, payload.filename, payload.engine,
        job_id=job_id, job_timeout="5m",
    )
    return {"job_id": job_id}
