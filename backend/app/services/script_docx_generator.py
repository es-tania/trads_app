"""
Génère le .docx du script scrapé à partir du JSON produit par scraper_script.py.

Portage Python fidèle de generate_script_docx.js (module 00) : même mise en
forme (titres d'épisode, dialogues colorés, choix, appels/messages...), mais
sans dépendance à Node.js — tout tourne maintenant dans le même processus
Python que le reste de l'API.
"""
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor, Mm

COLOR_HEADING2 = RGBColor(0x2E, 0x40, 0x57)
COLOR_PURPLE = RGBColor(0x7D, 0x3C, 0x98)
COLOR_BLUE = RGBColor(0x1A, 0x52, 0x76)
COLOR_GREEN = RGBColor(0x1E, 0x84, 0x49)

_KINDLED_HEADER_RE = re.compile(r"^(EPISODE \d+|KINDLED \d+|END|END OF KINDLED|START OF KINDLED)$", re.I)
_KINDLED_NUM_RE = re.compile(r"KINDLED \d+", re.I)
_CHOICE_NUM_RE = re.compile(r"^\d{2}\.\s")


def _add_run(paragraph, text, *, bold=False, italic=False, color=None, size=12):
    run = paragraph.add_run(text)
    run.font.name = "Poppins"
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    return run


def generate_docx(json_path: Path, output_path: Path) -> Path:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", "Script")
    script = data.get("script", "")

    doc = Document()
    doc.styles["Normal"].font.name = "Poppins"
    doc.styles["Normal"].font.size = Pt(12)

    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    for margin in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, margin, Pt(72))  # 1 inch

    # Titre principal
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_run(p, title.replace("Script:", "").strip(), bold=True, size=20)

    for raw_line in script.split("\n"):
        trimmed = raw_line.strip()
        if not trimmed:
            continue

        if trimmed.startswith("==") and trimmed.endswith("=="):
            continue

        if _KINDLED_HEADER_RE.match(trimmed):
            if _KINDLED_NUM_RE.search(trimmed) and trimmed != "KINDLED 1":
                continue
            if re.search(r"START OF KINDLED", trimmed, re.I):
                continue
            display_title = _KINDLED_NUM_RE.sub("KINDLED", trimmed)
            p = doc.add_paragraph()
            _add_run(p, display_title, bold=True, color=COLOR_HEADING2, size=14)
            continue

        if trimmed.startswith("——") or trimmed.startswith("--"):
            p = doc.add_paragraph()
            _add_run(p, "---", size=12)
            continue

        if trimmed.startswith("[Narration]"):
            text = trimmed.replace("[Narration]", "").strip()
            p = doc.add_paragraph()
            _add_run(p, text, size=11)
            continue

        if trimmed.startswith("***") and trimmed.endswith("***"):
            text = re.sub(r"^\*\*\*|\*\*\*$", "", trimmed).strip()
            p = doc.add_paragraph()
            _add_run(p, text, bold=True, size=12)
            continue

        if trimmed.startswith("*") and trimmed.endswith("*") and "KINDLED" not in trimmed:
            continue  # action/contexte, non transcrit

        if trimmed == "Choices:":
            p = doc.add_paragraph()
            _add_run(p, "Choices :", bold=True, color=COLOR_PURPLE, size=12)
            continue

        if _CHOICE_NUM_RE.match(trimmed):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(12)
            _add_run(p, trimmed, bold=True, color=COLOR_PURPLE, size=12)
            continue

        if " : " in trimmed:
            colon_idx = trimmed.index(" : ")
            speaker = trimmed[:colon_idx].strip()
            dialogue = trimmed[colon_idx + 3:].strip()
            if speaker == "Main Character":
                speaker = "Me"
            if speaker == "Personnage principal":
                speaker = "Moi"
            is_main = speaker in ("Me", "Moi")
            p = doc.add_paragraph()
            _add_run(p, speaker, bold=True, color=COLOR_BLUE if is_main else COLOR_GREEN, size=12)
            _add_run(p, " : ", size=12)
            _add_run(p, dialogue, size=12)
            continue

        if trimmed.startswith("[Appel -") or trimmed.startswith("[Fin appel]"):
            p = doc.add_paragraph()
            _add_run(p, trimmed, bold=True, color=COLOR_PURPLE, size=12)
            continue

        if trimmed.startswith("[Message -") or trimmed.startswith("[Fin message]"):
            p = doc.add_paragraph()
            _add_run(p, trimmed, bold=True, color=COLOR_BLUE, size=12)
            continue

        if (
            trimmed.startswith("[") and trimmed.endswith("]")
            and not trimmed.startswith("[Narration]")
            and not trimmed.startswith("[Appel")
            and not trimmed.startswith("[Fin")
            and not trimmed.startswith("[Message")
        ):
            text = trimmed[1:-1]
            p = doc.add_paragraph()
            _add_run(p, text, bold=True, italic=True, size=12)
            continue

        p = doc.add_paragraph()
        _add_run(p, trimmed, size=12)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
