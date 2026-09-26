#!/usr/bin/env python3
"""
Étape 0 : Extrait le texte d'un fichier .docx (traduction française)
et le convertit en .txt avec UNE LIGNE PAR PARAGRAPHE.

Compatible avec les caractères français :
é è ê ë à â î ï ô ù û ü ç œ æ ’ « »

Utilise Pandoc.

Installation de Pandoc :
    https://pandoc.org/installing.html

Usage :
    python 0_docx_to_txt.py texte_traduit.docx
    python 0_docx_to_txt.py texte_traduit.docx --output texte_traduit.txt
"""

import argparse
import subprocess
import sys
from pathlib import Path


def docx_to_paragraphs(docx_path: Path) -> list[str]:
    """
    Extrait les paragraphes d'un fichier DOCX.

    Chaque paragraphe Word devient une seule ligne dans le fichier TXT.
    Les retours à la ligne internes à un paragraphe sont remplacés par
    des espaces.
    """

    result = subprocess.run(
        [
            "pandoc",
            str(docx_path),
            "-t",
            "plain",
            "--wrap=none",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    raw_text = result.stdout

    # Normalisation des fins de ligne
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Pandoc sépare normalement les paragraphes par une ligne vide.
    blocks = raw_text.split("\n\n")

    paragraphs = []

    for block in blocks:
        # Supprime les espaces inutiles autour de chaque ligne,
        # puis rejoint les lignes d'un même paragraphe.
        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]

        joined = " ".join(lines).strip()

        if joined:
            paragraphs.append(joined)

    return paragraphs


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extrait le texte français d'un fichier .docx "
            "en .txt (une ligne = un paragraphe)."
        )
    )

    parser.add_argument(
        "docx",
        help="Chemin vers le fichier .docx",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Chemin du .txt de sortie "
             "(défaut : même nom que le .docx)",
    )

    args = parser.parse_args()

    docx_path = Path(args.docx)

    # Vérification du fichier d'entrée
    if not docx_path.exists():
        print(
            f"❌ Erreur : '{docx_path}' est introuvable.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not docx_path.is_file():
        print(
            f"❌ Erreur : '{docx_path}' n'est pas un fichier.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Extraction
    try:
        paragraphs = docx_to_paragraphs(docx_path)

    except FileNotFoundError:
        print(
            "❌ Erreur : Pandoc n'est pas installé "
            "ou n'est pas accessible depuis le PATH.",
            file=sys.stderr,
        )
        print(
            "Installation : https://pandoc.org/installing.html",
            file=sys.stderr,
        )
        sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("❌ Erreur lors de l'exécution de Pandoc.", file=sys.stderr)

        if e.stderr:
            print(e.stderr, file=sys.stderr)

        sys.exit(1)

    # Fichier de sortie
    output_path = (
        Path(args.output)
        if args.output
        else docx_path.with_suffix(".txt")
    )

    # Écriture explicite en UTF-8
    with open(
        output_path,
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:
        f.write("\n".join(paragraphs))

        if paragraphs:
            f.write("\n")

    # Résultat
    print(f"✅ {len(paragraphs)} paragraphes extraits.")
    print(f"✅ Résultat écrit dans : {output_path}")

    print("\n⚠️ Vérifie ce fichier avant l'étape suivante :")
    print("   • un paragraphe Word = une ligne dans le TXT")
    print("   • les accents français sont conservés")
    print("   • les apostrophes et caractères UTF-8 sont conservés")
    print("   • les retours à la ligne internes sont regroupés")
    print()
    print("   Idéalement, le nombre de lignes doit être proche")
    print("   du nombre de segments détectés par Whisper.")
    print()
    print("   Si un paragraphe contient plusieurs phrases qui doivent")
    print("   devenir des sous-titres séparés, découpe-le manuellement.")

    # Aperçu
    print("\n📄 Aperçu des 3 premières lignes :")

    for i, paragraph in enumerate(paragraphs[:3], start=1):
        print(f"  {i}. {paragraph}")


if __name__ == "__main__":
    main()
