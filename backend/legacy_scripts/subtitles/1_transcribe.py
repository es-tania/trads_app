#!/usr/bin/env python3
"""
Étape 1 : Transcrit l'audio/vidéo original avec Whisper
et exporte les segments avec leurs timecodes en JSON.

Usage :
    python 1_transcribe.py video.mp4 --model medium --lang en

Prérequis :
    pip install openai-whisper
    (+ ffmpeg installé sur le système : https://ffmpeg.org/download.html)
"""

import argparse
import json
import sys
from pathlib import Path


def transcribe(input_path: str, model_size: str = "medium", language: str | None = None) -> list[dict]:
    import whisper  # import local pour un message d'erreur plus clair si non installé

    print(f"[1/2] Chargement du modèle Whisper '{model_size}'...")
    model = whisper.load_model(model_size)

    print(f"[2/2] Transcription de '{input_path}'... (peut prendre plusieurs minutes)")
    result = model.transcribe(input_path, language=language, verbose=False)

    segments = [
        {
            "id": seg["id"],
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip(),
        }
        for seg in result["segments"]
    ]
    return segments


def main():
    parser = argparse.ArgumentParser(description="Transcrit une vidéo/audio avec Whisper et sort les segments timés.")
    parser.add_argument("input", help="Chemin vers le fichier vidéo ou audio")
    parser.add_argument("--model", default="medium",
                         help="Taille du modèle Whisper : tiny, base, small, medium, large (défaut: medium)")
    parser.add_argument("--lang", default=None,
                         help="Code langue de l'audio original (ex: en, es, de). Laisser vide pour auto-détection.")
    parser.add_argument("--output", default=None, help="Chemin du fichier JSON de sortie (défaut: <input>.segments.json)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Erreur : le fichier '{input_path}' n'existe pas.", file=sys.stderr)
        sys.exit(1)

    segments = transcribe(str(input_path), model_size=args.model, language=args.lang)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".segments.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(segments)} segments détectés.")
    print(f"✅ Résultat écrit dans : {output_path}")
    print("\nAperçu des 3 premiers segments :")
    for seg in segments[:3]:
        print(f"  [{seg['start']:.2f}s → {seg['end']:.2f}s] {seg['text']}")


if __name__ == "__main__":
    main()
