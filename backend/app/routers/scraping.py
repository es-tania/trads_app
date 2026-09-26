"""
Remplace le module 00 (n8n) : scraper une page de script, générer le docx EN,
traduire, générer le docx FR. Tout dans l'API, sans n8n.
"""
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.deepl_translate import translate_text
from app.services.scraper_script import scrape_script
from app.services.script_docx_generator import generate_docx

router = APIRouter(prefix="/scraping", tags=["scraping"])

SCRIPTS_DIR = settings.storage_dir / "scripts"


def _safe_folder_name(title: str) -> str:
    name = title.replace("Script:", "").strip()
    for ch in [":", "/", " ", "(", ")"]:
        name = name.replace(ch, "_")
    return name


class ScrapeRequest(BaseModel):
    url: str


class GenerateDocxRequest(BaseModel):
    folder: str
    filename: str
    lang: str = "EN"


class TranslateRequest(BaseModel):
    folder: str
    filename: str


@router.post("/scrape")
def scrape(payload: ScrapeRequest):
    """Récupère un script depuis une URL de wiki (remplace le noeud n8n de scraping)."""
    try:
        result = scrape_script(payload.url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Échec du scraping : {exc}") from exc

    folder = _safe_folder_name(result["title"])
    script_dir = SCRIPTS_DIR / folder
    script_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder}_{timestamp}.json"
    filepath = script_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return {"folder": folder, "file": filename, "title": result["title"]}


@router.post("/generate-docx")
def generate_docx_route(payload: GenerateDocxRequest):
    """Génère le .docx (EN ou FR) depuis le JSON scrapé — plus de dépendance Node.js."""
    json_path = SCRIPTS_DIR / payload.folder / payload.filename
    if not json_path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {json_path}")

    output_path = SCRIPTS_DIR / payload.folder / f"{payload.lang}.docx"
    generate_docx(json_path, output_path)
    return {"folder": payload.folder, "file": output_path.name}


@router.post("/translate")
def translate_scraped_script(payload: TranslateRequest):
    """Traduit le script scrapé via l'API officielle DeepL (remplace l'étape n8n)."""
    json_path = SCRIPTS_DIR / payload.folder / payload.filename
    if not json_path.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        original = json.load(f)

    translated_script = translate_text(original["script"], source_lang="EN", target_lang="FR")

    fr_filename = payload.filename.replace(".json", "_FR.json")
    fr_path = SCRIPTS_DIR / payload.folder / fr_filename
    with open(fr_path, "w", encoding="utf-8") as f:
        json.dump(
            {"title": original["title"], "url": original["url"], "script": translated_script},
            f, ensure_ascii=False, indent=2,
        )

    return {"folder": payload.folder, "file": fr_filename}
