"""
Remplace le module 01 (transcription d'images via `ollama launch claude`) :
upload de plusieurs images -> transcription par un modèle de vision local
(Ollama) -> un .docx au format script (noms en gras, noms de fichiers et
séparateurs en italique, via txt_to_docx).

La transcription passe par la file "subtitles" (et non "fast") : comme
Whisper, elle occupe le GPU, et les deux en même temps satureraient la VRAM.
Suivre l'avancement via GET /jobs/{job_id} ou WS /jobs/{job_id}/ws, puis
récupérer le .docx via GET /jobs/{job_id}/result.
"""
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.config import settings
from app.jobs.queue import queue_subtitles
from app.jobs.tasks import task_ocr_images
from app.services.job_meta import write_job_meta
from app.services.ocr_vision import OllamaError, list_vision_models

router = APIRouter(prefix="/ocr", tags=["ocr"])

JOBS_DIR = settings.storage_dir / "ocr_jobs"

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@router.get("/models")
def get_models():
    """Modèles de vision installés dans Ollama + modèle par défaut (OCR_MODEL)."""
    try:
        models = list_vision_models()
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"default": settings.ocr_model, "models": models}


@router.post("/images", status_code=202)
async def transcribe_images(files: list[UploadFile], model: str | None = Form(None)):
    """Upload d'une ou plusieurs images -> met la transcription en file d'attente.

    Les images sont transcrites dans l'ordre d'envoi (c'est le frontend qui
    fixe l'ordre). `model` : modèle Ollama à utiliser, OCR_MODEL (.env) si omis.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Aucune image envoyée")

    for upload in files:
        if Path(upload.filename or "").suffix.lower() not in _IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Format non supporté : {upload.filename!r} (attendu : {sorted(_IMAGE_EXTENSIONS)})",
            )

    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    filenames: list[str] = []
    for upload in files:
        # Path(...).name : ignore tout chemin envoyé par le client ; suffixe
        # en cas de doublon pour ne pas écraser une image déjà reçue.
        name = Path(upload.filename).name
        stem, suffix = Path(name).stem, Path(name).suffix
        n = 2
        while name in filenames:
            name = f"{stem}_{n}{suffix}"
            n += 1
        with open(job_dir / name, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        filenames.append(name)

    title = filenames[0] if len(filenames) == 1 else f"{len(filenames)} images ({filenames[0]}…)"
    write_job_meta(job_dir, title=title, model=model or settings.ocr_model)

    queue_subtitles.enqueue(
        task_ocr_images, job_id, str(job_dir), filenames, model,
        job_id=job_id, job_timeout="2h",
    )
    return {"job_id": job_id}
