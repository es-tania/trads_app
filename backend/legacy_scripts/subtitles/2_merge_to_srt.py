#!/usr/bin/env python3
"""
Étape 2 : Associe les timecodes du texte original (JSON produit par 1_transcribe.py)
au texte traduit, et génère un fichier .srt.

Le fichier texte traduit doit contenir UNE ligne = UN segment,
dans le même ordre que les segments détectés par Whisper.

Usage :
    python 2_merge_to_srt.py video.segments.json traduction.txt --output sous_titres.srt

Si le nombre de lignes traduites ne correspond pas exactement au nombre de
segments originaux, le script fait un mapping proportionnel automatique
(approximatif) et affiche un avertissement clair pour te permettre de
corriger le texte source si besoin.
"""

import argparse
import json
import sys
from pathlib import Path


def format_timecode(seconds: float) -> str:
    """Convertit des secondes en format SRT : HH:MM:SS,mmm"""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def load_translated_lines(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def map_lines_to_segments(segments: list[dict], lines: list[str]) -> list[dict]:
    """
    Cas idéal : même nombre de segments et de lignes -> mapping direct 1:1.
    Cas dégradé : nombres différents -> mapping proportionnel (approximatif),
    avec avertissement.
    """
    n_seg, n_lines = len(segments), len(lines)

    if n_seg == n_lines:
        return [{"start": seg["start"], "end": seg["end"], "text": line}
                for seg, line in zip(segments, lines)]

    print(f"⚠️  Attention : {n_seg} segments détectés dans l'audio original, "
          f"mais {n_lines} lignes dans le texte traduit.")
    print("⚠️  Mapping proportionnel automatique appliqué (approximatif).")
    print("⚠️  Vérifie et ajuste le .srt généré si la synchro n'est pas parfaite.\n")

    result = []
    for seg in segments:
        # position relative du segment dans la timeline (0.0 à 1.0)
        idx_ratio = seg["id"] / max(n_seg - 1, 1)
        line_idx = min(int(round(idx_ratio * (n_lines - 1))), n_lines - 1)
        result.append({"start": seg["start"], "end": seg["end"], "text": lines[line_idx]})
    return result


def write_srt(entries: list[dict], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(entries, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_timecode(entry['start'])} --> {format_timecode(entry['end'])}\n")
            f.write(f"{entry['text']}\n\n")


def main():
    parser = argparse.ArgumentParser(description="Fusionne timecodes originaux + texte traduit -> .srt")
    parser.add_argument("segments_json", help="Fichier JSON produit par 1_transcribe.py")
    parser.add_argument("translated_text", help="Fichier texte traduit (une ligne = un segment)")
    parser.add_argument("--output", default=None, help="Chemin du .srt de sortie (défaut: sous_titres.srt)")
    args = parser.parse_args()

    seg_path = Path(args.segments_json)
    txt_path = Path(args.translated_text)
    if not seg_path.exists():
        print(f"Erreur : '{seg_path}' introuvable.", file=sys.stderr)
        sys.exit(1)
    if not txt_path.exists():
        print(f"Erreur : '{txt_path}' introuvable.", file=sys.stderr)
        sys.exit(1)

    with open(seg_path, "r", encoding="utf-8") as f:
        segments = json.load(f)
    lines = load_translated_lines(str(txt_path))

    entries = map_lines_to_segments(segments, lines)

    output_path = args.output or "sous_titres.srt"
    write_srt(entries, output_path)

    print(f"✅ Fichier .srt généré : {output_path} ({len(entries)} entrées)")


if __name__ == "__main__":
    main()
