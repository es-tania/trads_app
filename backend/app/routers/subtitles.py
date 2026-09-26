"""
Remplace le module 03 : téléchargement YouTube automatique (yt-dlp) puis
enchaînement de tes scripts existants (0_docx_to_txt -> 1_align ->
1_fr_txt_to_segments -> 2_merge_to_srt -> 4_fix_srt_timings) via subprocess.

Choix assumé pour la Phase 1 : ne PAS réécrire la logique Whisper/alignement
(risque de régression) — on l'enchaîne automatiquement à la place. La
réécriture en fonctions Python importables (plus rapide, sans relancer un
interpréteur à chaque étape) peut venir en Phase 2 une fois que le flux
complet est validé de bout en bout.
"""
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import yt_dlp
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.services.docx_utils import docx_to_txt

router = APIRouter(prefix="/subtitles", tags=["subtitles"])

JOBS_DIR = settings.storage_dir / "subtitles_jobs"
SCRIPTS_DIR = settings.subtitles_scripts_dir


def _run(args: list[str], cwd: Path) -> None:
    result = subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Échec de {' '.join(args)} :\n{result.stderr[-2000:]}",
        )


def _download_youtube(url: str, job_dir: Path) -> Path:
    output_template = str(job_dir / "video.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    video_path = job_dir / "video.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=502, detail="Téléchargement YouTube échoué (fichier introuvable)")
    return video_path


@router.post("/generate")
async def generate_subtitles(
    en_docx: UploadFile,
    fr_docx: UploadFile,
    youtube_url: str | None = None,
    video: UploadFile | None = None,
    whisper_model: str = "medium",
    min_duration: float = 1.2,
):
    """
    Génère un .srt FR synchronisé, à partir soit d'un lien YouTube
    (téléchargé automatiquement), soit d'une vidéo uploadée directement.
    """
    if not youtube_url and not video:
        raise HTTPException(status_code=400, detail="Fournis soit youtube_url, soit un fichier vidéo")

    job_dir = JOBS_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)

    # 1. Récupération de la vidéo
    if youtube_url:
        video_path = _download_youtube(youtube_url, job_dir)
    else:
        video_path = job_dir / "video.mp4"
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)

    # 2. Sauvegarde des docx uploadés
    en_docx_path = job_dir / "EN.docx"
    fr_docx_path = job_dir / "FR.docx"
    with open(en_docx_path, "wb") as f:
        shutil.copyfileobj(en_docx.file, f)
    with open(fr_docx_path, "wb") as f:
        shutil.copyfileobj(fr_docx.file, f)

    # 3. docx -> txt (réutilise notre utilitaire Python, pas besoin de pandoc)
    en_txt_path = job_dir / "EN.txt"
    fr_txt_path = job_dir / "FR.txt"
    docx_to_txt(en_docx_path, en_txt_path)
    docx_to_txt(fr_docx_path, fr_txt_path)

    # 4. Enchaînement des scripts existants du module 03, inchangés
    segments_json = job_dir / "video.segments.json"
    _run([
        str(SCRIPTS_DIR / "1_align.py"), str(video_path), str(en_txt_path),
        "--model", whisper_model, "--lang", "en", "--output", str(segments_json),
    ], cwd=job_dir)

    segments_fr_json = job_dir / "video.segments.fr.json"
    _run([
        str(SCRIPTS_DIR / "1_fr_txt_to_segments.py"), str(segments_json), str(fr_txt_path),
        "--output", str(segments_fr_json),
    ], cwd=job_dir)

    srt_path = job_dir / "sous_titres.srt"
    _run([
        str(SCRIPTS_DIR / "2_merge_to_srt.py"), str(segments_fr_json), str(fr_txt_path),
        "--output", str(srt_path),
    ], cwd=job_dir)

    srt_final_path = job_dir / "sous_titres_corrige.srt"
    _run([
        str(SCRIPTS_DIR / "4_fix_srt_timings.py"), str(srt_path),
        "--min-duration", str(min_duration), "--output", str(srt_final_path),
    ], cwd=job_dir)

    return FileResponse(srt_final_path, filename="sous_titres.srt", media_type="text/plain")
