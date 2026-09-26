"""
Remplace le module 01 (transcription d'images via Claude Code interactif).

⚠️ STUB — non branché volontairement. À décider ensemble une fois que tu
auras testé la qualité d'un modèle de vision local (Ollama : Qwen2-VL,
MiniCPM-V, Llama 3.2 Vision) sur tes propres images, avec repli possible sur
l'API Claude si la qualité locale n'est pas suffisante.

La route et le format de réponse sont déjà prêts : il suffit de remplacer
le contenu de `_transcribe_image()` par l'appel réel (Ollama ou API Claude)
sans toucher au reste (upload, génération du docx final).
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.services.docx_utils import txt_to_docx

router = APIRouter(prefix="/ocr", tags=["ocr"])

JOBS_DIR = settings.storage_dir / "ocr_jobs"


def _transcribe_image(image_path: Path) -> str:
    """
    TODO : brancher ici le modèle de vision choisi.

    Option A (gratuit, local) :
        appel à Ollama (ex: qwen2-vl, minicpm-v) via son API HTTP locale
        (http://localhost:11434/api/generate) avec l'image encodée en base64.

    Option B (payant, fiable) :
        appel au SDK Anthropic (`anthropic.Anthropic().messages.create(...)`)
        avec l'image en pièce jointe, comme filet de sécurité si la qualité
        locale n'est pas suffisante sur certaines images.
    """
    raise HTTPException(
        status_code=501,
        detail="OCR non encore branché — voir le TODO dans app/routers/ocr.py",
    )


@router.post("/images")
async def transcribe_images(files: list[UploadFile]):
    """Upload d'une ou plusieurs images -> un .docx avec le texte transcrit."""
    job_dir = JOBS_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for upload in files:
        image_path = job_dir / upload.filename
        with open(image_path, "wb") as f:
            f.write(await upload.read())

        text = _transcribe_image(image_path)
        lines.append(upload.filename)
        lines.append(text)
        lines.append("---")

    txt_path = job_dir / "script_images.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    docx_path = job_dir / "script_images.docx"
    txt_to_docx(txt_path, docx_path)

    return FileResponse(
        docx_path,
        filename="script_images.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
