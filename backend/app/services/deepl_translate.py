"""
Traduction via l'API officielle DeepL.

Remplace :
- module 00 : l'appel DeepL fait côté n8n (opaque, plus de dépendance à n8n)
- module 02 : le client Node.js non officiel `deeplx` (instable, pas de garantie)

Les mots/noms à ne jamais traduire (personnages, termes techniques du jeu)
sont protégés avec des balises <keep>...</keep>, que DeepL sait ignorer
nativement via tag_handling="xml" + ignore_tags=["keep"]. C'est exactement
le même mécanisme que celui déjà utilisé dans /save/translation du module 00
("<keep>Main Character</keep>") — on le rend juste automatique.
"""
import re

import deepl

from app.config import settings
from app.services.protected_words import PROTECTED_WORDS, protect_with_tags

_translator: deepl.Translator | None = None


def _get_translator() -> deepl.Translator:
    global _translator
    if _translator is None:
        if not settings.deepl_api_key:
            raise RuntimeError(
                "DEEPL_API_KEY manquante : ajoute-la dans backend/.env "
                "(clé gratuite sur https://www.deepl.com/pro-api)"
            )
        _translator = deepl.Translator(settings.deepl_api_key)
    return _translator


def translate_text(text: str, source_lang: str = "EN", target_lang: str = "FR") -> str:
    """Traduit un texte en protégeant les noms propres et termes techniques."""
    translator = _get_translator()
    protected = protect_with_tags(text)

    result = translator.translate_text(
        protected,
        source_lang=source_lang,
        target_lang=target_lang,
        tag_handling="xml",
        ignore_tags=["keep"],
    )

    translated = result.text
    # Nettoie les balises <keep> restantes (DeepL les laisse autour du mot protégé)
    translated = re.sub(r"<keep>(.*?)</keep>", r"\1", translated)
    translated = translated.replace("Main Character", "Moi")
    return translated
