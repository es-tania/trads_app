# Commandes
```bash
python subtitle_generator_gui.py


python 0_docx_to_txt.py files\EN.docx --output files\EN.txt
python 0_docx_to_txt.py files\FR.docx --output files\FR.txt

python 1_align.py files\video.mp4 files\EN.txt --model medium --lang en

python 1_fr_txt_to_segments.py files\video.segments.json files\FR.txt

python 2_merge_to_srt.py files\video.segments.fr.json files\FR.txt --output sous_titres.srt

python 3_add_subtitles_to_video.py files\video.mp4 sous_titres.srt --mode burn --style modern

python 4_fix_srt_timings.py sous_titres.srt --min-duration 1.2

python -m PyInstaller --onefile --windowed subtitle_generator_gui.py

```