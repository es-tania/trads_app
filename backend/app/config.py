"""
Configuration centralisée de l'application.

Toutes les valeurs sensibles ou dépendantes de la machine (clés API, chemins)
viennent des variables d'environnement (.env) — plus aucun chemin en dur
comme dans les scripts d'origine (C:\\Users\\tanes\\...).
"""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/config.py -> app/ -> backend/. Sert d'ancrage pour tout chemin relatif,
# indépendamment du répertoire courant depuis lequel uvicorn/le worker sont
# lancés (voir le validateur ci-dessous pour pourquoi c'est nécessaire).
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Dossier racine où tout est stocké (scripts scrapés, jobs, résultats)
    storage_dir: Path = Path("storage")

    # Dossier contenant tes scripts existants du module 03 (Transcript YTB),
    # réutilisés tels quels via subprocess pour l'instant (Phase 1).
    subtitles_scripts_dir: Path = Path("legacy_scripts/subtitles")

    # DeepL officiel (palier gratuit : 500 000 caractères/mois)
    deepl_api_key: str = ""

    # Moteur de traduction par défaut, utilisé quand une route ne précise
    # pas explicitement `engine` : "deeplx" (CLI Node.js local, gratuit,
    # sans clé — voir services/deeplx_translate.py) ou "deepl" (API
    # officielle, payante au-delà du palier gratuit, clé requise).
    translate_engine: str = "deeplx"

    # Commande pour lancer Node.js (utilisé pour le CLI deeplx). Change-la si
    # `node` n'est pas dans ton PATH.
    node_bin: str = "node"

    # Dossier contenant le projet npm du CLI deeplx (package.json + node_modules
    # après un `npm install`). Chemin relatif au dossier backend/.
    deeplx_cli_dir: Path = Path("deeplx-cli")

    # Ollama (OCR des images via un modèle de vision local, voir
    # services/ocr_vision.py). Le modèle doit avoir la capacité "vision"
    # (vérifiable avec `ollama show <modèle>`).
    ollama_url: str = "http://localhost:11434"
    ocr_model: str = "qwen3.5:4b"

    # Durée pendant laquelle Ollama garde le modèle en VRAM après le dernier
    # appel. Court par défaut pour libérer le GPU (Whisper) rapidement.
    ollama_keep_alive: str = "2m"

    # FlareSolverr (contournement Cloudflare), tourne dans un conteneur Docker
    flaresolverr_url: str = "http://localhost:8191/v1"

    # Redis (file d'attente RQ + pub/sub pour les logs en direct)
    redis_url: str = "redis://localhost:6379/0"

    # Origines autorisées pour le frontend Next.js
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("storage_dir", "subtitles_scripts_dir", "deeplx_cli_dir")
    @classmethod
    def _resolve_absolute(cls, v: Path) -> Path:
        """
        Toujours renvoyer un chemin absolu, ancré sur backend/ s'il était
        relatif — jamais résolu par rapport au cwd courant du process.

        Sans ça : les chemins passés en argument à un sous-processus
        (1_align.py, etc.) sont résolus par Python par rapport au `cwd` de
        CE sous-processus, qu'on fixe volontairement au dossier du job pour
        que les scripts legacy y écrivent leurs fichiers temporaires. Un
        chemin relatif s'y retrouve donc doublement imbriqué dans le dossier
        du job au lieu de pointer vers backend/legacy_scripts/... — c'est
        exactement le bug qui empêchait /subtitles/generate de trouver
        1_align.py.
        """
        return v if v.is_absolute() else (BACKEND_DIR / v).resolve()


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
