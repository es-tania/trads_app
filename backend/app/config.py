"""
Configuration centralisée de l'application.

Toutes les valeurs sensibles ou dépendantes de la machine (clés API, chemins)
viennent des variables d'environnement (.env) — plus aucun chemin en dur
comme dans les scripts d'origine (C:\\Users\\tanes\\...).
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Dossier racine où tout est stocké (scripts scrapés, jobs, résultats)
    storage_dir: Path = Path("./storage")

    # Dossier contenant tes scripts existants du module 03 (Transcript YTB),
    # réutilisés tels quels via subprocess pour l'instant (Phase 1).
    subtitles_scripts_dir: Path = Path("legacy_scripts/subtitles")

    # DeepL officiel (palier gratuit : 500 000 caractères/mois)
    deepl_api_key: str = ""

    # FlareSolverr (contournement Cloudflare), tourne dans un conteneur Docker
    flaresolverr_url: str = "http://localhost:8191/v1"

    # Origines autorisées pour le frontend Next.js
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
