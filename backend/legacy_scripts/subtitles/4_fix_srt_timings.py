#!/usr/bin/env python3
"""
Étape 4 (correctif) : Corrige un fichier .srt dont certains sous-titres ont une
durée trop courte pour être visibles (souvent en fin de vidéo, quand l'alignement
a dû caser plusieurs phrases dans un intervalle de temps trop court).

Ce script :
  1. Impose une durée minimale à chaque sous-titre (--min-duration, défaut 1.2s)
  2. Si l'extension d'un sous-titre chevauche le suivant, repousse le suivant
     (et tous ceux d'après, en cascade) pour ne jamais avoir de chevauchement
  3. Affiche un résumé de toutes les entrées corrigées

Usage :
    python 4_fix_srt_timings.py sous_titres.srt --output sous_titres_corrige.srt
    python 4_fix_srt_timings.py sous_titres.srt --min-duration 1.5
"""

import argparse
import re
import sys
from pathlib import Path

TIMECODE_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)


def parse_timecode(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def format_timecode(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", content.strip())
    entries = []
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip() != ""]
        if len(lines) < 2:
            continue
        match = TIMECODE_RE.search(lines[1]) if not lines[0].isdigit() else TIMECODE_RE.search(lines[1])
        # La ligne 0 est l'index, la ligne 1 le timecode, le reste le texte
        timecode_line_idx = 1 if lines[0].strip().isdigit() else 0
        match = TIMECODE_RE.search(lines[timecode_line_idx])
        if not match:
            continue
        start = parse_timecode(*match.groups()[0:4])
        end = parse_timecode(*match.groups()[4:8])
        text = "\n".join(lines[timecode_line_idx + 1:])
        entries.append({"start": start, "end": end, "text": text})
    return entries


def fix_timings(entries: list[dict], min_duration: float) -> tuple[list[dict], list[str]]:
    log = []
    prev_end = float("-inf")
    for i, entry in enumerate(entries, start=1):
        original_start, original_end = entry["start"], entry["end"]

        if entry["start"] < prev_end:
            shift = prev_end - entry["start"]
            entry["start"] += shift
            entry["end"] += shift

        duration = entry["end"] - entry["start"]
        if duration < min_duration:
            entry["end"] = entry["start"] + min_duration

        if entry["start"] != original_start or entry["end"] != original_end:
            log.append(
                f"  #{i} \"{entry['text'][:40]}{'...' if len(entry['text']) > 40 else ''}\" : "
                f"{format_timecode(original_start)}→{format_timecode(original_end)} "
                f"corrigé en {format_timecode(entry['start'])}→{format_timecode(entry['end'])}"
            )

        prev_end = entry["end"]
    return entries, log


def write_srt(entries: list[dict], output_path: Path):
    with open(output_path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(entries, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_timecode(entry['start'])} --> {format_timecode(entry['end'])}\n")
            f.write(f"{entry['text']}\n\n")


def main():
    parser = argparse.ArgumentParser(description="Corrige les sous-titres trop courts pour être visibles.")
    parser.add_argument("srt", help="Fichier .srt à corriger")
    parser.add_argument("--min-duration", type=float, default=1.2,
                         help="Durée minimale par sous-titre en secondes (défaut: 1.2)")
    parser.add_argument("--output", default=None, help="Chemin du .srt corrigé (défaut: <srt>_corrige.srt)")
    args = parser.parse_args()

    srt_path = Path(args.srt)
    if not srt_path.exists():
        print(f"Erreur : '{srt_path}' introuvable.", file=sys.stderr)
        sys.exit(1)

    entries = parse_srt(srt_path)
    if not entries:
        print("Erreur : aucune entrée valide trouvée dans le fichier .srt.", file=sys.stderr)
        sys.exit(1)

    fixed_entries, log = fix_timings(entries, args.min_duration)

    output_path = Path(args.output) if args.output else srt_path.with_name(srt_path.stem + "_corrige.srt")
    write_srt(fixed_entries, output_path)

    print(f"✅ {len(fixed_entries)} sous-titres traités, durée minimale imposée : {args.min_duration}s")
    if log:
        print(f"\n{len(log)} entrées corrigées :")
        for line in log:
            print(line)
    else:
        print("Aucune correction nécessaire, tous les sous-titres avaient déjà une durée suffisante.")
    print(f"\n✅ Fichier corrigé écrit dans : {output_path}")


if __name__ == "__main__":
    main()
