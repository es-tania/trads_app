#!/usr/bin/env python3
"""
Étape 3 : Ajoute les sous-titres à la vidéo, soit :
  - "burn"  : incrustés définitivement dans l'image (visibles partout, mais non désactivables)
  - "embed" : piste de sous-titres séparée dans un .mkv (activable/désactivable, non modifiable à la volée)

Usage :
    python 3_add_subtitles_to_video.py video.mp4 sous_titres.srt --mode burn --style modern
    python 3_add_subtitles_to_video.py video.mp4 sous_titres.srt --mode burn --style bandeau
    python 3_add_subtitles_to_video.py video.mp4 sous_titres.srt --mode embed

Prérequis : ffmpeg installé et accessible dans le PATH.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Presets de style pour le mode "burn"
# Ce sont des paramètres ASS (Advanced SubStation) passés via force_style.
# Référence couleurs : format &HAABBGGRR (alpha, bleu, vert, rouge, en hexa)
# --------------------------------------------------------------------------
STYLES = {
    # Look "moderne" : police claire, gras, léger contour, ombre douce, pas de fond
    "modern": (
        "FontName=Arial,"
        "FontSize=13,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"   # blanc
        "OutlineColour=&H80000000,"   # noir semi-transparent
        "BorderStyle=1,"
        "Outline=2,"
        "Shadow=1,"
        "MarginV=40,"
        "Alignment=2"                  # centré en bas
    ),
    # Look "bandeau" : fond semi-transparent type sous-titres Netflix/YouTube
    "bandeau": (
        "FontName=Arial,"
        "FontSize=13,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "BackColour=&H90000000,"       # noir semi-transparent en fond de bloc
        "BorderStyle=3,"                # boîte pleine derrière le texte
        "Outline=0,"
        "Shadow=0,"
        "MarginV=40,"
        "Alignment=2"
    ),
    # Look "punchy" : accent coloré, bon pour réseaux sociaux
    "punchy": (
        "FontName=Arial Black,"
        "FontSize=14,"
        "Bold=1,"
        "PrimaryColour=&H0000FFFF,"    # jaune vif
        "OutlineColour=&H00000000,"    # noir
        "BorderStyle=1,"
        "Outline=3,"
        "Shadow=0,"
        "MarginV=50,"
        "Alignment=2"
    ),
    # Style minimal, proche de l'ancien rendu par défaut de ffmpeg
    "classic": (
        "FontName=Arial,"
        "FontSize=12,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=1,"
        "Shadow=0,"
        "MarginV=20,"
        "Alignment=2"
    ),
}


def burn_subtitles(video_path: Path, srt_path: Path, output_path: Path, style: str):
    # Le filtre subtitles= de ffmpeg a besoin d'un chemin échappé correctement
    srt_escaped = str(srt_path).replace("\\", "\\\\").replace(":", "\\:")

    force_style = STYLES.get(style, STYLES["modern"])
    subtitles_filter = f"subtitles={srt_escaped}:force_style='{force_style}'"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", subtitles_filter,
        "-c:a", "copy",
        str(output_path),
    ]
    print("Commande ffmpeg :", " ".join(cmd))
    subprocess.run(cmd, check=True)


def embed_subtitles(video_path: Path, srt_path: Path, output_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(srt_path),
        "-c", "copy",
        "-c:s", "srt",
        str(output_path),
    ]
    print("Commande ffmpeg :", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description="Ajoute des sous-titres à une vidéo via ffmpeg.")
    parser.add_argument("video", help="Fichier vidéo source")
    parser.add_argument("srt", help="Fichier .srt de sous-titres")
    parser.add_argument("--mode", choices=["burn", "embed"], default="burn",
                         help="burn = incrusté dans l'image, embed = piste séparée (défaut: burn)")
    parser.add_argument("--style", choices=list(STYLES.keys()), default="modern",
                         help="Style visuel des sous-titres incrustés (mode burn uniquement) : "
                              "modern (défaut), bandeau, punchy, classic")
    parser.add_argument("--output", default=None, help="Chemin du fichier de sortie")
    args = parser.parse_args()

    video_path = Path(args.video)
    srt_path = Path(args.srt)
    if not video_path.exists():
        print(f"Erreur : '{video_path}' introuvable.", file=sys.stderr)
        sys.exit(1)
    if not srt_path.exists():
        print(f"Erreur : '{srt_path}' introuvable.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        suffix = "_soustitre.mp4" if args.mode == "burn" else "_soustitre.mkv"
        output_path = video_path.with_name(video_path.stem + suffix)

    if args.mode == "burn":
        burn_subtitles(video_path, srt_path, output_path, args.style)
    else:
        embed_subtitles(video_path, srt_path, output_path)

    print(f"\n✅ Vidéo avec sous-titres générée : {output_path}")


if __name__ == "__main__":
    main()