"""
Tâches de fond exécutées par le worker RQ (voir run_worker.py).

Chaque fonction reçoit un job_id (généré par la route avant l'enqueue, donc
disponible côté client immédiatement) et journalise sa progression via
JobLogger, pour que l'API et le frontend puissent suivre l'avancement.
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yt_dlp

from app.config import settings
from app.jobs.logging import JobLogger
from app.services.docx_utils import docx_to_txt, txt_to_docx
from app.services.translation import translate_text
from app.services.scraper_script import scrape_script
from app.services.script_docx_generator import generate_docx

SCRAPING_DIR = settings.storage_dir / "scripts"


def _safe_folder_name(title: str) -> str:
    name = title.replace("Script:", "").strip()
    for ch in [":", "/", " ", "(", ")"]:
        name = name.replace(ch, "_")
    return name


def _run_streaming(args: list[str], cwd: Path, logger: JobLogger) -> None:
    """Lance un script legacy et journalise sa sortie ligne par ligne en direct."""
    process = subprocess.Popen(
        [sys.executable, *args], cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    for line in process.stdout:
        logger.log(line.rstrip())
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Échec de {' '.join(args)} (code {process.returncode})")


# ---------------------------------------------------------------------------
# Scraping (module 00)
# ---------------------------------------------------------------------------

def task_scrape(job_id: str, url: str) -> None:
    logger = JobLogger(job_id)
    logger.set_status("running")
    try:
        logger.log(f"Récupération de {url}...")
        result = scrape_script(url)

        folder = _safe_folder_name(result["title"])
        script_dir = SCRAPING_DIR / folder
        script_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{folder}_{timestamp}.json"
        with open(script_dir / filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.log(f"Script récupéré : {result['title']}")
        logger.set_status(
            "done",
            result_path=str(script_dir / filename),
            result_filename=filename,
            folder=folder,
            file=filename,
            title=result["title"],
        )
    except Exception as exc:
        logger.log(f"Erreur : {exc}")
        logger.set_status("error", message=str(exc))


def task_translate_scraped(job_id: str, folder: str, filename: str, engine: str | None = None) -> None:
    logger = JobLogger(job_id)
    logger.set_status("running")
    try:
        json_path = SCRAPING_DIR / folder / filename
        with open(json_path, "r", encoding="utf-8") as f:
            original = json.load(f)

        logger.log(f"Traduction via le moteur '{engine or settings.translate_engine}'...")
        translated_script = translate_text(original["script"], source_lang="EN", target_lang="FR", engine=engine)

        fr_filename = filename.replace(".json", "_FR.json")
        fr_path = SCRAPING_DIR / folder / fr_filename
        with open(fr_path, "w", encoding="utf-8") as f:
            json.dump(
                {"title": original["title"], "url": original["url"], "script": translated_script},
                f, ensure_ascii=False, indent=2,
            )

        logger.log("Traduction terminée")
        logger.set_status(
            "done", result_path=str(fr_path), result_filename=fr_filename,
            folder=folder, file=fr_filename,
        )
    except Exception as exc:
        logger.log(f"Erreur : {exc}")
        logger.set_status("error", message=str(exc))


# ---------------------------------------------------------------------------
# Traduction docx (module 02)
# ---------------------------------------------------------------------------

def task_translate_docx(job_id: str, job_dir: str, engine: str | None = None) -> None:
    logger = JobLogger(job_id)
    logger.set_status("running")
    try:
        job_path = Path(job_dir)
        en_docx = job_path / "EN.docx"
        en_txt = job_path / "EN.txt"

        logger.log("Extraction du texte du .docx...")
        docx_to_txt(en_docx, en_txt)

        with open(en_txt, "r", encoding="utf-8") as f:
            text = f.read()

        logger.log(f"Traduction via le moteur '{engine or settings.translate_engine}'...")
        translated = translate_text(text, source_lang="EN", target_lang="FR", engine=engine)

        fr_txt = job_path / "FR.txt"
        with open(fr_txt, "w", encoding="utf-8") as f:
            f.write(translated)

        fr_docx = job_path / "FR.docx"
        logger.log("Génération du .docx traduit...")
        txt_to_docx(fr_txt, fr_docx)

        logger.log("Terminé")
        logger.set_status("done", result_path=str(fr_docx), result_filename="FR.docx")
    except Exception as exc:
        logger.log(f"Erreur : {exc}")
        logger.set_status("error", message=str(exc))


# ---------------------------------------------------------------------------
# Sous-titres (module 03)
# ---------------------------------------------------------------------------

def _download_youtube(url: str, job_dir: Path, logger: JobLogger) -> Path:
    logger.log(f"Téléchargement de {url}...")
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
        raise RuntimeError("Téléchargement YouTube échoué (fichier introuvable)")
    logger.log("Téléchargement terminé")
    return video_path


def task_generate_subtitles(
    job_id: str, job_dir: str, youtube_url: str | None,
    whisper_model: str, min_duration: float,
) -> None:
    logger = JobLogger(job_id)
    logger.set_status("running")
    try:
        job_path = Path(job_dir)
        scripts_dir = settings.subtitles_scripts_dir

        video_path = job_path / "video.mp4"
        if youtube_url:
            video_path = _download_youtube(youtube_url, job_path, logger)
        elif not video_path.exists():
            raise RuntimeError("Aucune vidéo trouvée pour ce job")

        en_txt = job_path / "EN.txt"
        fr_txt = job_path / "FR.txt"
        logger.log("Extraction du texte des .docx...")
        docx_to_txt(job_path / "EN.docx", en_txt)
        docx_to_txt(job_path / "FR.docx", fr_txt)

        segments_json = job_path / "video.segments.json"
        logger.log(f"Alignement Whisper (modèle {whisper_model})... cela peut prendre plusieurs minutes")
        _run_streaming([
            str(scripts_dir / "1_align.py"), str(video_path), str(en_txt),
            "--model", whisper_model, "--lang", "en", "--output", str(segments_json),
        ], cwd=job_path, logger=logger)

        segments_fr_json = job_path / "video.segments.fr.json"
        logger.log("Mapping des segments FR...")
        _run_streaming([
            str(scripts_dir / "1_fr_txt_to_segments.py"), str(segments_json), str(fr_txt),
            "--output", str(segments_fr_json),
        ], cwd=job_path, logger=logger)

        srt_path = job_path / "sous_titres.srt"
        logger.log("Génération du .srt...")
        _run_streaming([
            str(scripts_dir / "2_merge_to_srt.py"), str(segments_fr_json), str(fr_txt),
            "--output", str(srt_path),
        ], cwd=job_path, logger=logger)

        srt_final_path = job_path / "sous_titres_corrige.srt"
        logger.log("Correction des timings...")
        _run_streaming([
            str(scripts_dir / "4_fix_srt_timings.py"), str(srt_path),
            "--min-duration", str(min_duration), "--output", str(srt_final_path),
        ], cwd=job_path, logger=logger)

        logger.log("Terminé")
        logger.set_status("done", result_path=str(srt_final_path), result_filename="sous_titres.srt")
    except Exception as exc:
        logger.log(f"Erreur : {exc}")
        logger.set_status("error", message=str(exc))
