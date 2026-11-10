"""
Remplace le module 03 : téléchargement YouTube (yt-dlp) + enchaînement des
scripts legacy, exécutés en tâche de fond (RQ, file "subtitles") — la
requête HTTP ne bloque plus pendant les minutes que peut prendre Whisper.

Suivre l'avancement via GET /jobs/{job_id} ou en direct via WS /jobs/{job_id}/ws.
"""
import shutil
import uuid

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.jobs.logging import JobLogger
from app.jobs.queue import queue_subtitles
from app.jobs.tasks import task_generate_subtitles
from app.services.job_meta import write_job_meta

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

    write_job_meta(
        job_dir,
        title=youtube_url or (video.filename if video else "Vidéo uploadée"),
        source="youtube" if youtube_url else "upload",
        whisper_model=whisper_model,
    )

    JobLogger(job_id).set_status("queued")
    queue_subtitles.enqueue(
        task_generate_subtitles,
        job_id, str(job_dir), youtube_url, whisper_model, min_duration,
        job_id=job_id, job_timeout="30m",
    )

    return {"job_id": job_id}


_SRT_FILES = {"fr": "sous_titres_corrige.srt", "en": "sous_titres_en_corrige.srt"}


@router.get("/{job_id}/srt/{lang}")
def download_srt(job_id: str, lang: str):
    """Télécharge le .srt final d'un job : lang = "fr" (traduit) ou "en" (original)."""
    filename = _SRT_FILES.get(lang)
    if filename is None:
        raise HTTPException(status_code=404, detail=f"Langue inconnue : {lang!r} (attendu : fr ou en)")
    if job_id in (".", "..") or "\\" in job_id:
        raise HTTPException(status_code=400, detail="Identifiant invalide")

    path = JOBS_DIR / job_id / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Ce .srt n'existe pas pour ce job (job antérieur à cette fonctionnalité ?)")
    return FileResponse(path, filename=f"sous_titres_{lang}.srt")


@router.get("/{job_id}/video")
def download_video(job_id: str):
    """
    Récupère la vidéo du job (téléchargée via yt-dlp, ou celle uploadée
    directement). Disponible dès que le téléchargement est terminé, pas
    besoin d'attendre la fin de tout le job.
    """
    video_path = JOBS_DIR / job_id / "video.mp4"
    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Vidéo pas encore disponible pour ce job (ou job introuvable)",
        )
    return FileResponse(video_path, filename="video.mp4")
