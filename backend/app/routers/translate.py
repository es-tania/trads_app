"""
Remplace le module 02 : traduire un .docx EN en FR, sans deeplx/Node.js.
Upload direct depuis le frontend, réponse = fichier .docx traduit.
"""
import shutil
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.services.deepl_translate import translate_text
from app.services.docx_utils import docx_to_txt, txt_to_docx

router = APIRouter(prefix="/translate", tags=["translate"])

JOBS_DIR = settings.storage_dir / "translate_jobs"


@router.post("/docx")
async def translate_docx(file: UploadFile):
    """Upload d'un .docx EN -> retourne le .docx FR traduit."""
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .docx sont acceptés")

    job_dir = JOBS_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)

    en_docx = job_dir / "EN.docx"
    with open(en_docx, "wb") as f:
        shutil.copyfileobj(file.file, f)

    en_txt = job_dir / "EN.txt"
    docx_to_txt(en_docx, en_txt)

    with open(en_txt, "r", encoding="utf-8") as f:
        text = f.read()

    translated = translate_text(text, source_lang="EN", target_lang="FR")

    fr_txt = job_dir / "FR.txt"
    with open(fr_txt, "w", encoding="utf-8") as f:
        f.write(translated)

    fr_docx = job_dir / "FR.docx"
    txt_to_docx(fr_txt, fr_docx)

    return FileResponse(
        fr_docx,
        filename="FR.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
