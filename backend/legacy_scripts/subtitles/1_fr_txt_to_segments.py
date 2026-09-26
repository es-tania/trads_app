#!/usr/bin/env python3
"""
Remplace le texte anglais d'un video.segments.json par la traduction
française contenue dans un FR.txt, tout en conservant les timings.

Entrées :
    video.segments.json
    FR.txt

Sortie :
    video.segments.fr.json (par défaut)

Le principe est une correspondance 1:1 :
    segment JSON #0 <-> ligne 1 de FR.txt
    segment JSON #1 <-> ligne 2 de FR.txt
    etc.

Le script refuse de continuer si le nombre de lignes non vides du TXT
ne correspond pas au nombre de segments JSON. Cela évite de décaler
silencieusement toute la synchronisation.

Usage :
    python 1_fr_txt_to_segments.py video.segments.json FR.txt

    python 1_fr_txt_to_segments.py video.segments.json FR.txt \
        --output video.segments.json
"""

import argparse
import json
import sys
from pathlib import Path


def read_french_lines(txt_path: Path) -> list[str]:
    """Lit FR.txt en UTF-8 et retourne une ligne = un segment."""
    with txt_path.open("r", encoding="utf-8-sig") as f:
        lines = f.read().splitlines()

    # On ignore uniquement les lignes complètement vides.
    # Les espaces en début/fin sont supprimés.
    return [line.strip() for line in lines if line.strip()]


def load_segments(json_path: Path) -> list[dict]:
    """Charge et vérifie la structure de video.segments.json."""
    with json_path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(
            "Le JSON doit contenir une liste de segments à la racine."
        )

    for i, segment in enumerate(data):
        if not isinstance(segment, dict):
            raise ValueError(
                f"Le segment #{i} n'est pas un objet JSON."
            )

        for key in ("id", "start", "end", "text"):
            if key not in segment:
                raise ValueError(
                    f"Le segment #{i} ne contient pas la clé '{key}'."
                )

    return data


def create_french_segments(
    segments: list[dict],
    french_lines: list[str],
) -> list[dict]:
    """Copie les segments et remplace uniquement leur champ 'text'."""

    if len(segments) != len(french_lines):
        raise ValueError(
            "\n"
            "Nombre de lignes différent !\n"
            f"  Segments JSON : {len(segments)}\n"
            f"  Lignes FR.txt : {len(french_lines)}\n"
            "\n"
            "Le script s'arrête pour éviter de décaler les sous-titres.\n"
            "Vérifie que FR.txt contient exactement une ligne par segment."
        )

    result = []

    for segment, french_text in zip(segments, french_lines):
        new_segment = segment.copy()
        new_segment["text"] = french_text
        result.append(new_segment)

    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Remplace les textes d'un video.segments.json par "
            "les lignes d'un FR.txt en conservant les timings."
        )
    )

    parser.add_argument(
        "segments_json",
        help="Fichier video.segments.json original",
    )

    parser.add_argument(
        "fr_txt",
        help="Fichier FR.txt contenant une ligne par segment",
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Fichier JSON de sortie. "
            "Par défaut : <nom>.segments.fr.json"
        ),
    )

    args = parser.parse_args()

    json_path = Path(args.segments_json)
    txt_path = Path(args.fr_txt)

    # Vérification des fichiers
    if not json_path.exists():
        print(
            f"❌ Erreur : '{json_path}' est introuvable.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not txt_path.exists():
        print(
            f"❌ Erreur : '{txt_path}' est introuvable.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Nom de sortie
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = json_path.with_name(
            json_path.stem + ".fr.json"
        )

    try:
        segments = load_segments(json_path)
        french_lines = read_french_lines(txt_path)

        french_segments = create_french_segments(
            segments,
            french_lines,
        )

        # ensure_ascii=False est important pour conserver :
        # é è ê ë à â î ï ô ù û ü ç œ æ « » etc.
        with output_path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as f:
            json.dump(
                french_segments,
                f,
                ensure_ascii=False,
                indent=2,
            )
            f.write("\n")

    except json.JSONDecodeError as e:
        print(
            f"❌ JSON invalide : {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    print("✅ Conversion terminée.")
    print(f"   Segments : {len(french_segments)}")
    print(f"   Source   : {json_path}")
    print(f"   Texte FR : {txt_path}")
    print(f"   Sortie   : {output_path}")

    print("\n📋 Aperçu :")
    for segment in french_segments[:3]:
        print(
            f"   [{segment['start']:.2f} → {segment['end']:.2f}] "
            f"{segment['text']}"
        )


if __name__ == "__main__":
    main()
