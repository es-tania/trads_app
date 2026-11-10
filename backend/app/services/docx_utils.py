"""
Conversions docx <-> txt, adaptées de :
- 02_Trad_FR/translate_pipeline.py (docx_to_txt)
- 01_Script_image_trad_FR/convert_to_docx.py (txt_to_docx)

Paramétrées par chemins (au lieu de noms de fichiers en dur) pour être
réutilisables depuis n'importe quelle route de l'API.
"""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


def docx_to_txt(input_docx: Path, output_txt: Path) -> None:
    doc = Document(str(input_docx))
    with open(output_txt, "w", encoding="utf-8") as f:
        for para in doc.paragraphs:
            f.write(para.text + "\n")


def txt_to_docx(input_txt: Path, output_docx: Path) -> None:
    with open(input_txt, "r", encoding="utf-8") as f:
        lines = f.readlines()

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Poppins"
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        from docx.oxml import OxmlElement
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), "Poppins")

    for raw_line in lines:
        line = raw_line.strip("\n")
        if not line:
            doc.add_paragraph("")
            continue

        if ":" in line:
            name_part = line.split(":", 1)[0].strip()
            # "??" / "???" : interlocuteur inconnu, à mettre en gras comme un nom.
            is_unknown_speaker = name_part and set(name_part) == {"?"}
            if len(name_part) < 30 and (is_unknown_speaker or not any(c in name_part for c in ".,!?()")):
                text_part = line.split(":", 1)[1].lstrip(" ")
                p = doc.add_paragraph()
                run = p.add_run(name_part + ": ")
                run.bold = True
                p.add_run(text_part)
                continue

        if line.endswith(".png") or line.lower().endswith(".jpg") or line == "---":
            p = doc.add_paragraph(line)
            if p.runs:
                p.runs[0].italic = True
        else:
            doc.add_paragraph(line)

    doc.save(str(output_docx))
