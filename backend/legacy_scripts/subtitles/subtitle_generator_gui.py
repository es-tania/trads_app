#!/usr/bin/env python3
"""
Interface graphique — génère un fichier .srt synchronisé à partir de :
  - une vidéo
  - un texte original EN (.docx)
  - une traduction FR (.docx)

Sans ligne de commande : tout se fait par sélecteurs de fichiers natifs
(explorateur Windows / Finder macOS / gestionnaire de fichiers Linux).

Pipeline interne (reprend la logique validée de 0_docx_to_txt.py, 1_align.py,
1_fr_txt_to_segments.py et 4_fix_srt_timings.py, réunie en un seul outil) :

    1. Extraction du texte de EN.docx et FR.docx (via Pandoc)
    2. Alignement forcé de l'audio original sur le texte EN (stable-ts)
    3. Remplacement du texte EN par le texte FR (mêmes timecodes)
    4. Application d'une durée minimale par sous-titre (anti sous-titres invisibles)
    5. Écriture du .srt final à l'emplacement de ton choix

3_add_subtitles_to_video.py n'est PAS utilisé ici (volontairement) — il reste
disponible séparément si tu veux incruster les sous-titres dans la vidéo plus tard.

Prérequis (une seule fois) :
    pip install -U stable-ts
    Pandoc installé : https://pandoc.org/installing.html
    ffmpeg installé et accessible dans le PATH : https://ffmpeg.org/download.html

Lancement :
    python subtitle_generator_gui.py
"""

import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# ---------------------------------------------------------------------------
# Logique métier (adaptée de 0_docx_to_txt.py / 1_align.py /
# 1_fr_txt_to_segments.py / 4_fix_srt_timings.py)
# ---------------------------------------------------------------------------


def docx_to_paragraphs(docx_path: Path) -> list[str]:
    """Extrait le texte d'un .docx : un paragraphe Word = une ligne."""
    result = subprocess.run(
        ["pandoc", str(docx_path), "-t", "plain", "--wrap=none"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    raw_text = result.stdout.replace("\r\n", "\n").replace("\r", "\n")
    blocks = raw_text.split("\n\n")
    paragraphs = []
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        joined = " ".join(lines).strip()
        if joined:
            paragraphs.append(joined)
    return paragraphs


def align_audio(video_path: Path, en_paragraphs: list[str], model_size: str, language: str, log) -> list[dict]:
    """Alignement forcé : trouve les timecodes de chaque ligne de en_paragraphs dans l'audio."""
    import stable_whisper

    log(f"Chargement du modèle Whisper '{model_size}' (peut être long au premier lancement)...")
    model = stable_whisper.load_model(model_size)

    original_text = "\n".join(en_paragraphs)
    log(f"Alignement de l'audio sur {len(en_paragraphs)} lignes de texte original... (patiente, ça peut prendre plusieurs minutes)")
    result = model.align(str(video_path), original_text, language=language, original_split=True)

    data = result.to_dict()
    segments = [
        {"id": i, "start": round(seg["start"], 3), "end": round(seg["end"], 3), "text": seg["text"].strip()}
        for i, seg in enumerate(data["segments"])
    ]
    return segments


def substitute_french_text(segments: list[dict], fr_paragraphs: list[str]) -> list[dict]:
    """Remplace le texte EN de chaque segment par la ligne FR correspondante (1:1)."""
    result = []
    for seg, fr_text in zip(segments, fr_paragraphs):
        new_seg = dict(seg)
        new_seg["text"] = fr_text
        result.append(new_seg)
    return result


def format_timecode(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fix_timings(entries: list[dict], min_duration: float) -> tuple[list[dict], list[str]]:
    """Impose une durée minimale par sous-titre, en repoussant les suivants en cascade."""
    log_lines = []
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
            log_lines.append(
                f"  #{i} corrigé : {format_timecode(original_start)}→{format_timecode(original_end)} "
                f"devient {format_timecode(entry['start'])}→{format_timecode(entry['end'])}"
            )
        prev_end = entry["end"]
    return entries, log_lines


def write_srt(entries: list[dict], output_path: Path):
    with open(output_path, "w", encoding="utf-8") as f:
        for i, entry in enumerate(entries, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_timecode(entry['start'])} --> {format_timecode(entry['end'])}\n")
            f.write(f"{entry['text']}\n\n")


# ---------------------------------------------------------------------------
# Interface graphique
# ---------------------------------------------------------------------------

MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]


class SubtitleGeneratorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Générateur de sous-titres FR synchronisés")
        self.root.geometry("720x640")
        self.root.minsize(640, 560)

        self.video_path = tk.StringVar()
        self.en_docx_path = tk.StringVar()
        self.fr_docx_path = tk.StringVar()
        self.output_srt_path = tk.StringVar()
        self.model_size = tk.StringVar(value="medium")
        self.language = tk.StringVar(value="en")
        self.min_duration = tk.StringVar(value="1.2")
        self.apply_min_duration = tk.BooleanVar(value=True)
        self.keep_debug_files = tk.BooleanVar(value=True)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None

        self._build_ui()
        self._poll_log_queue()

    # -- Construction de l'interface -----------------------------------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        frame_inputs = ttk.LabelFrame(self.root, text="1. Fichiers")
        frame_inputs.pack(fill="x", **pad)

        self._add_file_row(frame_inputs, "Vidéo :", self.video_path,
                            self._browse_video, row=0)
        self._add_file_row(frame_inputs, "Texte original (EN, .docx) :", self.en_docx_path,
                            lambda: self._browse_docx(self.en_docx_path), row=1)
        self._add_file_row(frame_inputs, "Traduction (FR, .docx) :", self.fr_docx_path,
                            lambda: self._browse_docx(self.fr_docx_path), row=2)
        self._add_file_row(frame_inputs, "Enregistrer le .srt sous :", self.output_srt_path,
                            self._browse_output, row=3)

        frame_options = ttk.LabelFrame(self.root, text="2. Options")
        frame_options.pack(fill="x", **pad)

        ttk.Label(frame_options, text="Modèle Whisper :").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        model_combo = ttk.Combobox(frame_options, textvariable=self.model_size, values=MODEL_SIZES,
                                    state="readonly", width=12)
        model_combo.grid(row=0, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(frame_options, text="Langue de l'audio (code) :").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(frame_options, textvariable=self.language, width=8).grid(row=0, column=3, sticky="w", padx=8, pady=6)

        ttk.Checkbutton(frame_options, text="Imposer une durée minimale par sous-titre",
                         variable=self.apply_min_duration).grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Entry(frame_options, textvariable=self.min_duration, width=8).grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(frame_options, text="secondes").grid(row=1, column=3, sticky="w", padx=0, pady=6)

        ttk.Checkbutton(frame_options, text="Conserver les fichiers intermédiaires (debug : EN.txt, FR.txt, segments.json)",
                         variable=self.keep_debug_files).grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=6)

        frame_action = ttk.Frame(self.root)
        frame_action.pack(fill="x", **pad)

        self.run_button = ttk.Button(frame_action, text="▶  Générer les sous-titres", command=self._on_run_clicked)
        self.run_button.pack(side="left")

        self.progress = ttk.Progressbar(frame_action, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True, padx=12)

        frame_log = ttk.LabelFrame(self.root, text="3. Journal")
        frame_log.pack(fill="both", expand=True, **pad)

        self.log_widget = scrolledtext.ScrolledText(frame_log, height=16, state="disabled", wrap="word")
        self.log_widget.pack(fill="both", expand=True, padx=6, pady=6)

    def _add_file_row(self, parent, label, var, browse_cmd, row):
        ttk.Label(parent, text=label, width=28, anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(parent, text="Parcourir…", command=browse_cmd).grid(row=row, column=2, sticky="e", padx=8, pady=6)
        parent.grid_columnconfigure(1, weight=1)

    # -- Sélecteurs de fichiers -------------------------------------------

    def _browse_video(self):
        path = filedialog.askopenfilename(
            title="Choisir la vidéo",
            filetypes=[("Fichiers vidéo", "*.mp4 *.mkv *.mov *.avi *.webm"), ("Tous les fichiers", "*.*")],
        )
        if path:
            self.video_path.set(path)
            if not self.output_srt_path.get():
                self.output_srt_path.set(str(Path(path).with_suffix(".srt")))

    def _browse_docx(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            title="Choisir le fichier .docx",
            filetypes=[("Documents Word", "*.docx"), ("Tous les fichiers", "*.*")],
        )
        if path:
            var.set(path)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Enregistrer le fichier de sous-titres",
            defaultextension=".srt",
            filetypes=[("Sous-titres SRT", "*.srt"), ("Tous les fichiers", "*.*")],
        )
        if path:
            self.output_srt_path.set(path)

    # -- Journal (thread-safe) -------------------------------------------

    def _log(self, message: str):
        self.log_queue.put(message)

    def _poll_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_widget.configure(state="normal")
                self.log_widget.insert("end", message + "\n")
                self.log_widget.see("end")
                self.log_widget.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)

    # -- Validation et lancement -------------------------------------------

    def _validate_inputs(self) -> tuple[Path, Path, Path, Path, float] | None:
        video = self.video_path.get().strip()
        en_docx = self.en_docx_path.get().strip()
        fr_docx = self.fr_docx_path.get().strip()
        output_srt = self.output_srt_path.get().strip()

        if not video or not Path(video).exists():
            messagebox.showerror("Fichier manquant", "Sélectionne une vidéo valide.")
            return None
        if not en_docx or not Path(en_docx).exists():
            messagebox.showerror("Fichier manquant", "Sélectionne le fichier .docx du texte original (EN).")
            return None
        if not fr_docx or not Path(fr_docx).exists():
            messagebox.showerror("Fichier manquant", "Sélectionne le fichier .docx de la traduction (FR).")
            return None
        if not output_srt:
            messagebox.showerror("Emplacement manquant", "Choisis où enregistrer le fichier .srt.")
            return None

        min_dur = 0.0
        if self.apply_min_duration.get():
            try:
                min_dur = float(self.min_duration.get().replace(",", "."))
                if min_dur <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Valeur invalide", "La durée minimale doit être un nombre positif (ex: 1.2).")
                return None

        return Path(video), Path(en_docx), Path(fr_docx), Path(output_srt), min_dur

    def _on_run_clicked(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        validated = self._validate_inputs()
        if validated is None:
            return

        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", "end")
        self.log_widget.configure(state="disabled")

        self.run_button.configure(state="disabled")
        self.progress.start(12)

        self.worker_thread = threading.Thread(target=self._run_pipeline, args=validated, daemon=True)
        self.worker_thread.start()

    def _finish(self, success: bool, message: str):
        def _update():
            self.progress.stop()
            self.run_button.configure(state="normal")
            if success:
                messagebox.showinfo("Terminé", message)
            else:
                messagebox.showerror("Erreur", message)
        self.root.after(0, _update)

    # -- Pipeline (exécuté dans un thread séparé) -------------------------

    def _run_pipeline(self, video: Path, en_docx: Path, fr_docx: Path, output_srt: Path, min_dur: float):
        try:
            debug_dir = None
            if self.keep_debug_files.get():
                debug_dir = output_srt.parent / f"{output_srt.stem}_debug"
                debug_dir.mkdir(parents=True, exist_ok=True)

            self._log("Extraction du texte original (EN)...")
            en_paragraphs = docx_to_paragraphs(en_docx)
            self._log(f"  → {len(en_paragraphs)} paragraphes extraits de {en_docx.name}")

            self._log("Extraction du texte traduit (FR)...")
            fr_paragraphs = docx_to_paragraphs(fr_docx)
            self._log(f"  → {len(fr_paragraphs)} paragraphes extraits de {fr_docx.name}")

            if debug_dir:
                (debug_dir / "EN.txt").write_text("\n".join(en_paragraphs) + "\n", encoding="utf-8")
                (debug_dir / "FR.txt").write_text("\n".join(fr_paragraphs) + "\n", encoding="utf-8")

            if len(en_paragraphs) != len(fr_paragraphs):
                self._finish(
                    False,
                    "Le nombre de paragraphes ne correspond pas entre les deux .docx :\n\n"
                    f"  EN.docx : {len(en_paragraphs)} paragraphes\n"
                    f"  FR.docx : {len(fr_paragraphs)} paragraphes\n\n"
                    "Corrige le découpage dans Word (un paragraphe = un sous-titre) "
                    "pour que les deux comptes soient identiques, puis relance."
                )
                return

            self._log("Alignement audio ↔ texte original (peut prendre plusieurs minutes)...")
            segments = align_audio(video, en_paragraphs, self.model_size.get(), self.language.get(), self._log)
            self._log(f"  → {len(segments)} segments alignés (attendu : {len(en_paragraphs)})")

            if debug_dir:
                import json
                (debug_dir / f"{video.stem}.segments.json").write_text(
                    json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8"
                )

            if len(segments) != len(fr_paragraphs):
                self._finish(
                    False,
                    "L'alignement n'a pas produit le bon nombre de segments :\n\n"
                    f"  Segments alignés : {len(segments)}\n"
                    f"  Lignes FR.docx   : {len(fr_paragraphs)}\n\n"
                    + (f"Les fichiers de debug ont été conservés dans :\n{debug_dir}\n\n" if debug_dir else "")
                    + "Vérifie que EN.docx correspond exactement à ce qui est prononcé dans la vidéo."
                )
                return

            self._log("Remplacement du texte EN par le texte FR (mêmes timecodes)...")
            fr_segments = substitute_french_text(segments, fr_paragraphs)

            if self.apply_min_duration.get():
                self._log(f"Application d'une durée minimale de {min_dur}s par sous-titre...")
                fr_segments, fix_log = fix_timings(fr_segments, min_dur)
                if fix_log:
                    self._log(f"{len(fix_log)} sous-titres ajustés :")
                    for line in fix_log:
                        self._log(line)
                else:
                    self._log("  → aucun ajustement nécessaire.")

            output_srt.parent.mkdir(parents=True, exist_ok=True)
            write_srt(fr_segments, output_srt)
            self._log(f"\n✅ Fichier .srt généré : {output_srt}")

            self._finish(True, f"Sous-titres générés avec succès :\n\n{output_srt}")

        except FileNotFoundError as e:
            self._log(f"❌ Erreur : {e}")
            self._finish(False, "Pandoc ou ffmpeg est introuvable. Vérifie qu'ils sont installés et dans le PATH.")
        except subprocess.CalledProcessError as e:
            self._log(f"❌ Erreur Pandoc : {e.stderr}")
            self._finish(False, f"Erreur lors de l'extraction d'un .docx :\n\n{e.stderr}")
        except ImportError:
            self._log("❌ Erreur : le module 'stable-ts' n'est pas installé.")
            self._finish(False, "Le module 'stable-ts' n'est pas installé.\nLance : pip install -U stable-ts")
        except Exception as e:  # noqa: BLE001 - on veut afficher toute erreur inattendue à l'utilisateur
            self._log(f"❌ Erreur inattendue : {e}")
            self._finish(False, f"Une erreur inattendue s'est produite :\n\n{e}")


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except tk.TclError:
        pass
    app = SubtitleGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
