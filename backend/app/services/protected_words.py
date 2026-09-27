"""
Liste commune des mots à ne jamais traduire (personnages, termes techniques
du jeu), partagée entre tous les moteurs de traduction (DeepL officiel,
DeepLX local...).

Deux stratégies de protection sont fournies :
- `protect_with_tags` : balises <keep>...</keep>, que DeepL sait ignorer
  nativement via tag_handling="xml" + ignore_tags=["keep"].
- `protect_with_placeholders` / `restore_placeholders` : jetons opaques
  (ex. "XKEEP3X"), pour les moteurs qui ne gèrent pas le XML/HTML côté API
  (comme DeepLX). Un moteur de traduction n'a normalement aucune raison de
  traduire un jeton alphanumérique sans espace ni ponctuation.
"""
import re

PROTECTED_WORDS = [
    # Noms de personnages
    "Rafayel", "Sylus", "Zayne", "Xavier", "Caleb",
    "Jeremiah", "Isaiah", "Soren", "Valko", "Gideon", "Aemma", "Iann",
    # Termes techniques
    "Wanderer", "Wanderers", "Hunter", "Aether Core", "Protofield",
    "Protocore", "Deepspace Tunnel", "Evolver", "Evol",
    "Deepspace Academy", "Chronorift", "Protocurve",
    "Metaflux", "Backtrackers", "EVER", "UNICORNS", "hunter", "hunters",
    "Deepspace Hunter", "Deepspace Hunters", "Deepspace",
    "KINDLED", "Memoria", "Linkon", "Lemuria",
]


def protect_with_tags(text: str) -> str:
    for word in sorted(PROTECTED_WORDS, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(word)}\b", f"<keep>{word}</keep>", text)
    return text


def protect_with_placeholders(text: str) -> tuple[str, dict[str, str]]:
    """Remplace chaque mot protégé présent dans `text` par un jeton unique.

    Renvoie le texte modifié ainsi que la correspondance jeton -> mot
    d'origine, à repasser à `restore_placeholders` une fois la traduction
    faite.
    """
    mapping: dict[str, str] = {}
    for i, word in enumerate(sorted(PROTECTED_WORDS, key=len, reverse=True)):
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, text):
            token = f"XKEEP{i}X"
            text = re.sub(pattern, token, text)
            mapping[token] = word
    return text, mapping


def restore_placeholders(text: str, mapping: dict[str, str]) -> str:
    for token, word in mapping.items():
        text = text.replace(token, word)
    return text
