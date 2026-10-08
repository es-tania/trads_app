"""
Point d'entrée unique pour la traduction, utilisé par les tâches de fond
(app/jobs/tasks.py). Choisit le moteur selon le paramètre `engine` passé par
l'appelant ou, à défaut, TRANSLATE_ENGINE dans .env :

- "deeplx" : CLI Node.js `deeplx` en local (gratuit, sans clé, nécessite
             Node.js + `npm install` dans backend/deeplx-cli/). Moteur par
             défaut.
- "deepl"  : API officielle DeepL (payante au-delà du palier gratuit,
             clé requise, mais protection <keep> robuste).
"""
from app.config import settings
from app.services import deepl_translate, deeplx_translate

ENGINES = {"deepl", "deeplx"}


def translate_text(
    text: str,
    source_lang: str = "EN",
    target_lang: str = "FR",
    engine: str | None = None,
) -> str:
    resolved_engine = (engine or settings.translate_engine or "deeplx").lower()

    if resolved_engine == "deeplx":
        return deeplx_translate.translate_text(text, source_lang=source_lang, target_lang=target_lang)
    if resolved_engine == "deepl":
        return deepl_translate.translate_text(text, source_lang=source_lang, target_lang=target_lang)

    raise ValueError(f"Moteur de traduction inconnu : {resolved_engine!r} (attendu : {sorted(ENGINES)})")
