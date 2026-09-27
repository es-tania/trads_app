"""
Traduction via le CLI Node.js `deeplx` (paquet npm `deeplx`, port du célèbre
OwO-Network/DeepLX) — exactement le même outil que celui utilisé dans
02_Trad_FR/translate_pipeline.py, mais appelé proprement depuis Python.

Contrairement au script d'origine :
- pas de fichiers temporaires (`chunk_1.txt`, ...) : le texte est passé
  directement en argument (`--text`) ;
- pas de `shell=True` ni de dépendance au PATH pour trouver `deeplx` : on
  appelle `node` directement sur le fichier `lib/cli.js` du paquet, résolu
  depuis `deeplx-cli/node_modules/` (voir DEEPLX_CLI_DIR dans .env) ;
- les mots protégés (personnages, termes techniques) sont automatiques,
  comme pour le moteur DeepL (voir protected_words.py), au lieu d'être
  gérés à la main.

Installation (une seule fois) :
    cd backend/deeplx-cli
    npm install
"""
import subprocess

from app.config import settings
from app.services.protected_words import protect_with_placeholders, restore_placeholders

# Le CLI deeplx relaie l'API web gratuite de DeepL, limitée en taille de
# requête. On découpe le texte par paragraphes pour rester sous une limite
# raisonnable (identique à l'ancien translate_pipeline.py).
_MAX_CHUNK_CHARS = 1400
_MAX_RETRIES = 3
_TIMEOUT_SECONDS = 30


def _cli_js_path():
    cli_js = settings.deeplx_cli_dir / "node_modules" / "deeplx" / "lib" / "cli.js"
    if not cli_js.exists():
        raise RuntimeError(
            f"CLI deeplx introuvable ({cli_js}).\n"
            f"Installe-le une fois avec :\n"
            f"  cd {settings.deeplx_cli_dir} && npm install"
        )
    return cli_js


def _split_text(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    chunks = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break

        # Coupe sur le dernier retour à la ligne avant la limite, pour ne
        # jamais couper une ligne en deux.
        split_idx = text.rfind("\n", 0, max_chars)
        if split_idx == -1:
            split_idx = max_chars

        chunks.append(text[:split_idx])
        text = text[split_idx:].lstrip("\n")
    return chunks


def _translate_chunk(cli_js, text: str, source_lang: str, target_lang: str) -> str:
    args = [
        settings.node_bin, str(cli_js),
        "-s", source_lang, "-t", target_lang,
        "--text", text,
    ]

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=_TIMEOUT_SECONDS,
                check=True,
            )
            return result.stdout.strip("\n")
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Impossible de lancer Node.js (commande '{settings.node_bin}' introuvable). "
                "Installe Node.js et vérifie qu'il est dans le PATH, ou ajuste NODE_BIN dans backend/.env."
            ) from exc
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            last_error = exc

    detail = getattr(last_error, "stderr", None) or str(last_error)
    raise RuntimeError(f"Échec de la traduction via deeplx (CLI Node.js) après {_MAX_RETRIES} tentatives : {detail}")


def translate_text(text: str, source_lang: str = "EN", target_lang: str = "FR") -> str:
    """Traduit un texte via le CLI Node.js deeplx, en protégeant les noms propres/termes techniques."""
    cli_js = _cli_js_path()
    protected, mapping = protect_with_placeholders(text)

    translated_chunks = [
        _translate_chunk(cli_js, chunk, source_lang, target_lang)
        for chunk in _split_text(protected)
    ]
    translated = "\n".join(translated_chunks)

    translated = restore_placeholders(translated, mapping)
    translated = translated.replace("Main Character", "Moi")
    return translated
