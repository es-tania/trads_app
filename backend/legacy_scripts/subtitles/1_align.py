#!/usr/bin/env python3
"""
Étape 1 (bis) : Alignement forcé de l'audio original avec SON PROPRE script texte
(au lieu d'une transcription "à l'aveugle" par Whisper).

Pourquoi ce script plutôt que 1_transcribe.py ?
------------------------------------------------
1_transcribe.py fait transcrire l'audio par Whisper sans rien connaître du texte :
Whisper invente ses propres coupures de segments, qui ne correspondent presque
jamais exactement au découpage en paragraphes de ta traduction. Résultat : le
script 2_merge_to_srt.py doit deviner un mapping proportionnel (approximatif).

Ce script fait l'inverse : tu lui donnes le texte EXACT qui est prononcé dans
la vidéo (EN.txt, un paragraphe = une ligne, comme pour le .docx traduit).
Le modèle ne "devine" plus le texte, il trouve seulement les timecodes de
CHAQUE LIGNE que tu lui donnes. Le nombre de segments produits est donc
GARANTI égal au nombre de lignes de EN.txt.

-> Si ton .docx traduit a le même découpage en paragraphes que EN.txt
   (ce qui est déjà ta méthode de travail), le mapping avec 2_merge_to_srt.py
   devient exact, sans approximation.

Prérequis :
    pip install -U stable-ts
    (stable-ts embarque Whisper, pas besoin de réinstaller openai-whisper à part)
    + ffmpeg installé et dans le PATH

Usage :
    python 1_align.py video.mp4 EN.txt --model medium --lang en --output video.segments.json
"""

import argparse
import json
import sys
from pathlib import Path


def align(input_path: str, text_path: str, model_size: str, language: str) -> list[dict]:
    import stable_whisper  # import local pour un message d'erreur plus clair si non installé

    print(f"[1/2] Chargement du modèle Whisper '{model_size}' (via stable-ts)...")
    model = stable_whisper.load_model(model_size)

    with open(text_path, "r", encoding="utf-8") as f:
        original_text = f.read()

    n_lines = len([l for l in original_text.splitlines() if l.strip()])
    print(f"[2/2] Alignement de '{input_path}' sur {n_lines} lignes de '{text_path}'...")
    print("      (peut prendre plusieurs minutes)")

    result = model.align(
        input_path,
        original_text,
        language=language,
        original_split=True,  # respecte les retours à la ligne comme limites de segments
    )

    data = result.to_dict()
    segments = [
        {
            "id": i,
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip(),
        }
        for i, seg in enumerate(data["segments"])
    ]
    return segments


def main():
    parser = argparse.ArgumentParser(
        description="Aligne l'audio/vidéo original sur SON PROPRE texte (forced alignment, via stable-ts)."
    )
    parser.add_argument("input", help="Chemin vers le fichier vidéo ou audio")
    parser.add_argument("text", help="Chemin vers le .txt du texte ORIGINAL (même langue que l'audio), une ligne = un paragraphe")
    parser.add_argument("--model", default="medium",
                         help="Taille du modèle Whisper : tiny, base, small, medium, large (défaut: medium)")
    parser.add_argument("--lang", default="en",
                         help="Code langue de l'audio ET du texte original (ex: en, es, de). Défaut : en")
    parser.add_argument("--output", default=None, help="Chemin du fichier JSON de sortie (défaut: <input>.segments.json)")
    args = parser.parse_args()

    input_path = Path(args.input)
    text_path = Path(args.text)
    if not input_path.exists():
        print(f"Erreur : le fichier '{input_path}' n'existe pas.", file=sys.stderr)
        sys.exit(1)
    if not text_path.exists():
        print(f"Erreur : le fichier '{text_path}' n'existe pas.", file=sys.stderr)
        sys.exit(1)

    try:
        segments = align(str(input_path), str(text_path), model_size=args.model, language=args.lang)
    except ImportError:
        print("Erreur : stable-ts n'est pas installé. Lance : pip install -U stable-ts", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".segments.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    with open(text_path, "r", encoding="utf-8") as f:
        n_lines = len([l for l in f if l.strip()])

    print(f"\n✅ {len(segments)} segments alignés (attendu : {n_lines} lignes dans '{text_path}').")
    if len(segments) != n_lines:
        print("⚠️  Le nombre de segments ne correspond pas exactement au nombre de lignes !")
        print("    Vérifie EN.txt (lignes vides isolées, ponctuation, etc.) et réessaie.")
    print(f"✅ Résultat écrit dans : {output_path}")
    print("\nAperçu des 3 premiers segments :")
    for seg in segments[:3]:
        print(f"  [{seg['start']:.2f}s → {seg['end']:.2f}s] {seg['text']}")


if __name__ == "__main__":
    main()
