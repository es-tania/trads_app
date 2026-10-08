"""
Historique des éléments stockés sur disque (scripts scrapés, traductions
docx, sous-titres) : lister, télécharger un fichier, supprimer un élément.

Contrairement au statut des jobs (Redis, expire après 24h), ce qui est dans
storage/ reste tant que tu ne le supprimes pas : cette vue est donc durable.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.jobs.logging import JobLogger

router = APIRouter(prefix="/storage", tags=["storage"])

CATEGORY_DIRS = {
    "scripts": settings.storage_dir / "scripts",
    "translate": settings.storage_dir / "translate_jobs",
    "subtitles": settings.storage_dir / "subtitles_jobs",
}

# Catégories dont l'identifiant d'élément est un job_id (donc suivi dans Redis).
_JOB_CATEGORIES = {"translate", "subtitles"}
_ACTIVE_STATUSES = ("queued", "running")


def _item_dir(category: str, item_id: str) -> Path:
    base = CATEGORY_DIRS.get(category)
    if base is None:
        raise HTTPException(status_code=404, detail=f"Catégorie inconnue : {category!r}")
    if not item_id or "/" in item_id or "\\" in item_id or item_id in (".", ".."):
        raise HTTPException(status_code=400, detail="Identifiant invalide")
    path = base / item_id
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Élément introuvable")
    return path


def _read_meta(item_dir: Path) -> dict:
    meta_path = item_dir / "meta.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _script_title(item_dir: Path) -> str | None:
    for json_file in sorted(item_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and data.get("title"):
            return data["title"]
    return None


def _job_status(category: str, item_id: str) -> str | None:
    if category not in _JOB_CATEGORIES:
        return None
    try:
        return JobLogger(item_id).get_status().get("status")
    except Exception:
        return None  # Redis indisponible ou job expiré : on n'affiche pas de statut


@router.get("")
def list_items():
    items = []
    for category, base in CATEGORY_DIRS.items():
        if not base.is_dir():
            continue
        for item_dir in base.iterdir():
            if not item_dir.is_dir():
                continue

            meta = _read_meta(item_dir)
            files_paths = [p for p in item_dir.iterdir() if p.is_file() and p.name != "meta.json"]
            title = meta.get("title")
            if not title and category == "scripts":
                title = _script_title(item_dir)

            created_at = meta.get("created_at") or datetime.fromtimestamp(
                item_dir.stat().st_mtime, tz=timezone.utc
            ).isoformat()

            items.append({
                "category": category,
                "id": item_dir.name,
                "title": title or item_dir.name,
                "created_at": created_at,
                "files": sorted(p.name for p in files_paths),
                "size_bytes": sum(p.stat().st_size for p in files_paths),
                "status": _job_status(category, item_dir.name),
                "details": {k: v for k, v in meta.items() if k not in ("title", "created_at")},
            })

    items.sort(key=lambda i: i["created_at"], reverse=True)
    return items


@router.get("/{category}/{item_id}/download")
def download_file(category: str, item_id: str, file: str):
    item_dir = _item_dir(category, item_id)
    if not file or "/" in file or "\\" in file or file in (".", ".."):
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")
    path = item_dir / file
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(path, filename=file)


@router.delete("/{category}/{item_id}")
def delete_item(category: str, item_id: str):
    item_dir = _item_dir(category, item_id)
    if _job_status(category, item_id) in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Ce job est encore en cours : arrête-le avant de le supprimer.",
        )
    shutil.rmtree(item_dir)
    return {"ok": True}
