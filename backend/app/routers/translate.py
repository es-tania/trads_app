"""
Remplace le module 02 : traduire un .docx EN en FR (DeepL ou DeepLX local).
Upload direct -> mis en file d'attente ("fast") -> récupérer le résultat via
GET /jobs/{job_id}/result une fois le job terminé.
"""
import shutil
import uuid

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.config import settings
from app.jobs.queue import queue_fast
from app.jobs.tasks import task_translate_docx
from app.services.job_meta import write_job_meta
from app.services.translation import ENGINES

router = APIRouter(prefix="/translate", tags=["translate"])

JOBS_DIR = settings.storage_dir / "translate_jobs"


@router.post("/docx", status_code=202)
async def translate_docx(file: UploadFile, engine: str | None = Form(None)):
    """Upload d'un .docx EN -> met la traduction en file d'attente.

    `engine` : "deepl" (API officielle) ou "deeplx" (CLI local). Si omis,
    utilise TRANSLATE_ENGINE défini dans .env.
    """
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .docx sont acceptés")

    if engine is not None and engine.lower() not in ENGINES:
        raise HTTPException(status_code=400, detail=f"Moteur inconnu : {engine!r} (attendu : {sorted(ENGINES)})")

    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    en_docx = job_dir / "EN.docx"
    with open(en_docx, "wb") as f:
        shutil.copyfileobj(file.file, f)

    write_job_meta(job_dir, title=file.filename, engine=engine or settings.translate_engine)

    queue_fast.enqueue(task_translate_docx, job_id, str(job_dir), engine, job_id=job_id, job_timeout="5m")
    return {"job_id": job_id}
