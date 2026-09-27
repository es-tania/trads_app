"""
Remplace le module 02 : traduire un .docx EN en FR, sans deeplx/Node.js.
Upload direct -> mis en file d'attente -> récupérer le résultat via
GET /jobs/{job_id}/result une fois le job terminé.
"""
import shutil
import uuid

from fastapi import APIRouter, HTTPException, UploadFile

from app.config import settings
from app.jobs.queue import queue
from app.jobs.tasks import task_translate_docx

router = APIRouter(prefix="/translate", tags=["translate"])

JOBS_DIR = settings.storage_dir / "translate_jobs"


@router.post("/docx", status_code=202)
async def translate_docx(file: UploadFile):
    """Upload d'un .docx EN -> met la traduction en file d'attente."""
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .docx sont acceptés")

    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    en_docx = job_dir / "EN.docx"
    with open(en_docx, "wb") as f:
        shutil.copyfileobj(file.file, f)

    queue.enqueue(task_translate_docx, job_id, str(job_dir), job_timeout="5m")
    return {"job_id": job_id}
