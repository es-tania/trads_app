"""
Transcription d'images de script via un modèle de vision local (Ollama).

Remplace le workflow du module 01 (`ollama launch claude` + AGENTS.md) : au
lieu d'un agent qui lit les images une à une, on envoie directement chaque
image au modèle via l'API HTTP d'Ollama (/api/chat), avec une consigne
stricte sur le format de sortie attendu par txt_to_docx (`Nom: réplique`).
"""
import base64
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from app.config import settings

PROMPT = """This image is a screenshot from a story game. Transcribe ALL the text visible in it, exactly as written, in its original language (do not translate, do not correct, do not summarize).

Output rules:
- One line per dialogue line or text block, in reading order (top to bottom).
- When a character name is shown for a line of dialogue (often displayed on its own line, above the indented dialogue), write the name and the dialogue on the SAME line: Name: text
- If the speaker's name is hidden or shown as "???", write: ??: text (always with the colon).
- Narration or text without a speaker: write the text alone on its line.
- Choices offered to the player: one choice per line.
- Ignore interface elements: phone status bar (time, battery percentage, network), buttons, icons, menus.
- Output ONLY the transcription, with no introduction, comment or markdown.

Example of expected output:
Tane: Where were you?
??: Somewhere you can't follow.
The door slams shut behind her."""

_THINK_RE = re.compile(r"<think>.*?</think>", re.S)

# Barre d'état du téléphone que le modèle recopie parfois malgré la consigne
# (ex: "12:45", "12:45 87%") — sinon txt_to_docx prendrait "12" pour un nom.
_STATUS_BAR_RE = re.compile(r"^\d{1,2}:\d{2}(\s*(AM|PM))?(\s+\d{1,3}\s*%)?$", re.I)


class OllamaError(RuntimeError):
    pass


def _post(path: str, payload: dict, timeout: float) -> dict:
    try:
        res = requests.post(f"{settings.ollama_url}{path}", json=payload, timeout=timeout)
    except requests.ConnectionError:
        raise OllamaError(
            f"Ollama ne répond pas sur {settings.ollama_url} — est-il lancé ? (`ollama serve`)"
        )
    if not res.ok:
        try:
            detail = res.json().get("error", res.text)
        except ValueError:
            detail = res.text
        raise OllamaError(f"Erreur Ollama ({res.status_code}) : {detail}")
    return res.json()


def list_vision_models() -> list[str]:
    """Modèles Ollama installés qui supportent les images."""
    try:
        res = requests.get(f"{settings.ollama_url}/api/tags", timeout=5)
        res.raise_for_status()
    except requests.RequestException:
        raise OllamaError(
            f"Ollama ne répond pas sur {settings.ollama_url} — est-il lancé ? (`ollama serve`)"
        )

    names = [model["name"] for model in res.json().get("models", [])]

    def _has_vision(name: str) -> bool:
        info = _post("/api/show", {"model": name}, timeout=30)
        return "vision" in info.get("capabilities", [])

    # /api/show peut prendre plusieurs secondes par modèle : on les interroge en parallèle.
    with ThreadPoolExecutor(max_workers=8) as pool:
        flags = list(pool.map(_has_vision, names))
    return sorted(name for name, ok in zip(names, flags) if ok)


def transcribe_image(image_path: Path, model: str | None = None) -> str:
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    data = _post(
        "/api/chat",
        {
            "model": model or settings.ocr_model,
            "messages": [{"role": "user", "content": PROMPT, "images": [image_b64]}],
            "stream": False,
            # La "réflexion" des modèles Qwen ralentit beaucoup sans améliorer
            # une simple transcription.
            "think": False,
            "options": {"temperature": 0},
            "keep_alive": settings.ollama_keep_alive,
        },
        # Un gros modèle qui déborde sur le CPU peut mettre plusieurs minutes par image.
        timeout=600,
    )
    text = data.get("message", {}).get("content", "")
    text = _THINK_RE.sub("", text)
    lines = [line.strip() for line in text.strip().splitlines()]
    lines = [line for line in lines if line and not _STATUS_BAR_RE.match(line)]
    return "\n".join(_join_speaker_lines(lines))


def _looks_like_speaker(line: str) -> bool:
    """Nom de personnage seul sur sa ligne : court, sans ponctuation de phrase."""
    if set(line) == {"?"}:
        return True
    return (
        len(line) <= 30
        and len(line.split()) <= 4
        and line[0].isupper()
        and not any(c in line for c in ".,!?:;()\"…—")
    )


def _join_speaker_lines(lines: list[str]) -> list[str]:
    """
    Le jeu affiche le nom AU-DESSUS de la réplique : le modèle suit souvent la
    consigne `Nom: réplique`, mais pas toujours (selon l'image). On rattache
    donc ici un nom isolé à la ligne qui le suit, pour un format constant.
    """
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if nxt is not None and _looks_like_speaker(line) and not _looks_like_speaker(nxt):
            result.append(f"{line}: {nxt}")
            i += 2
        else:
            result.append(line)
            i += 1
    return result
