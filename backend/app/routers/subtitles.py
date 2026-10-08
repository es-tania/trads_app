"""
Remplace le module 03 : téléchargement YouTube (yt-dlp) + enchaînement des
scripts legacy, exécutés en tâche de fond (RQ) — la requête HTTP ne bloque
plus pendant les minutes que peut prendre Whisper.

Suivre l'avancement via GET /jobs/{job_id} ou en direct via WS /jobs/{job_id}/ws.
"""
import shutil
import uuid

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.config import settings
from app.jobs.logging import JobLogger
from app.jobs.queue import queue
from app.jobs.tasks import task_generate_subtitles

router = APIRouter(prefix="/subtitles", tags=["subtitles"])

JOBS_DIR = settings.storage_dir / "subtitles_jobs"


@router.post("/generate", status_code=202)
async def generate_subtitles(
    en_docx: UploadFile,
    fr_docx: UploadFile,
    youtube_url: str | None = Form(None),
    video: UploadFile | None = None,
    whisper_model: str = Form("medium"),
    min_duration: float = Form(1.2),
):
    if not youtube_url and not video:
        raise HTTPException(status_code=400, detail="Fournis soit youtube_url, soit un fichier vidéo")

    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # La vidéo uploadée est sauvegardée ici (dans la requête) car l'objet
    # UploadFile ne survivrait pas jusqu'au worker. Le téléchargement
    # YouTube, lui, se fait dans la tâche de fond (peut être long).
    if video:
        with open(job_dir / "video.mp4", "wb") as f:
            shutil.copyfileobj(video.file, f)

    with open(job_dir / "EN.docx", "wb") as f:
        shutil.copyfileobj(en_docx.file, f)
    with open(job_dir / "FR.docx", "wb") as f:
        shutil.copyfileobj(fr_docx.file, f)

    JobLogger(job_id).set_status("queued")
    queue.enqueue(
        task_generate_subtitles,
        job_id, str(job_dir), youtube_url, whisper_model, min_duration,
        job_id=job_id, job_timeout="30m",
    )

    return {"job_id": job_id}
