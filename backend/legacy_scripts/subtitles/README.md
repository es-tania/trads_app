# Sous-titres automatiques (audio original + texte traduit)

Génère des sous-titres `.srt` en français, synchronisés sur les timecodes de
l'audio original, à partir d'une vidéo et de deux fichiers `.docx` (texte
original EN + traduction FR).

## 🖱️ Interface graphique (recommandé — pas de ligne de commande)

`subtitle_generator_gui.py` ouvre une fenêtre avec des sélecteurs de fichiers
natifs (explorateur Windows / Finder macOS / gestionnaire de fichiers Linux) :

```bash
python subtitle_generator_gui.py
```

1. Sélectionne ta vidéo, ton `.docx` EN, ton `.docx` FR, et l'emplacement où
   enregistrer le `.srt`
2. Choisis le modèle Whisper et la durée minimale par sous-titre si besoin
3. Clique sur **"Générer les sous-titres"**

Le journal en bas de la fenêtre affiche la progression en direct. Un dossier
`<nom_du_srt>_debug/` est créé à côté du `.srt` (EN.txt, FR.txt,
segments.json) pour que tu puisses inspecter ce qui a été détecté si la
synchro ne te convient pas — désactivable via la case "Conserver les
fichiers intermédiaires".

`3_add_subtitles_to_video.py` (incrustation dans la vidéo) n'est **pas**
utilisé par cette interface — il reste disponible séparément si tu veux
incruster les sous-titres dans l'image plus tard, avec ses styles visuels
(`modern`, `bandeau`, `punchy`, `classic`).

## 1. Installation (une seule fois)

```bash
# ffmpeg (nécessaire pour Whisper)
# macOS : brew install ffmpeg
# Ubuntu/Debian : sudo apt install ffmpeg
# Windows : https://ffmpeg.org/download.html

pip install -U stable-ts

# pandoc (nécessaire pour extraire le texte des .docx)
# macOS : brew install pandoc
# Ubuntu/Debian : sudo apt install pandoc
# Windows : https://pandoc.org/installing.html

# tkinter (interface graphique) — inclus nativement avec Python sur
# Windows et macOS. Sur Linux, si l'interface ne se lance pas :
# Ubuntu/Debian : sudo apt install python3-tk
```

> Note : le premier lancement de Whisper télécharge le modèle choisi (`tiny` à `large`).
> `medium` est un bon compromis vitesse/qualité pour commencer. `large` est plus précis
> mais plus lent (et demande plus de RAM/VRAM).

## 2. Utilisation en ligne de commande (alternative, si tu préfères scripter)

Ton texte traduit est dans deux `.docx` (EN et FR). Structure chaque document
avec **un paragraphe Word = un sous-titre** (touche Entrée entre chaque
phrase qui doit devenir un segment séparé), dans le même ordre dans les deux
fichiers.

```bash
# Étape 0 : extraire le texte des .docx -> EN.txt / FR.txt
python 0_docx_to_txt.py EN.docx --output EN.txt
python 0_docx_to_txt.py FR.docx --output FR.txt

# Étape 1 : aligner l'audio original sur le texte EN -> video.segments.json
python 1_align.py video.mp4 EN.txt --model medium --lang en

# Étape 1bis : remplacer le texte EN par le texte FR (mêmes timecodes)
python 1_fr_txt_to_segments.py video.segments.json FR.txt

# Étape 2 : formatage final en .srt
python 2_merge_to_srt.py video.segments.fr.json FR.txt --output sous_titres.srt

# Étape 4 : imposer une durée minimale par sous-titre
python 4_fix_srt_timings.py sous_titres.srt --min-duration 1.2

# Étape 3 (optionnelle) : incruster les sous-titres dans la vidéo
python 3_add_subtitles_to_video.py video.mp4 sous_titres_corrige.srt --mode burn --style modern
```

Voir `command.md` pour la liste de commandes prête à copier-coller.

## 3. Utilisation automatisée avec n8n (alternative)

Le fichier `workflow_n8n.json` contient un workflow prêt à importer :

1. Ouvre n8n → menu **⋮** → **Import from File** → sélectionne `workflow_n8n.json`
2. Ouvre le nœud **"Variables (à éditer)"** et remplace les chemins par les tiens :
   - `video_path` : chemin vers ta vidéo
   - `translated_docx_path` : chemin vers ton fichier `.docx` traduit
   - `scripts_dir` : dossier où sont les 4 scripts Python
   - `whisper_model` : `tiny`, `base`, `small`, `medium` ou `large`
   - `output_mode` : `burn` (incrusté) ou `embed` (piste séparée, sortie `.mkv`)
3. Clique sur **"Execute Workflow"**

Le workflow enchaîne automatiquement les 4 scripts via des nœuds **Execute Command**.
Tu peux ensuite le déclencher autrement (webhook, watch de dossier, etc.) selon tes besoins.

## Limites à connaître

- La correspondance segment original ↔ paragraphe traduit fonctionne mieux si le
  découpage est fait à la main dans Word (1 paragraphe = 1 phrase/segment). Si les
  comptes ne correspondent pas, le script 2 applique un mapping proportionnel
  automatique (approximatif) et t'avertit — vérifie alors le `.srt` généré et ajuste
  si besoin.
- Si ton `.docx` contient des titres, listes à puces ou tableaux en plus du texte
  traduit, `0_docx_to_txt.py` les convertira aussi en lignes de texte brut — nettoie
  le `.txt` généré si ton document contient autre chose que la traduction pure.
- Le mode `burn` grave les sous-titres définitivement dans l'image (non désactivables).
  Le mode `embed` les garde en piste séparée mais nécessite un conteneur `.mkv`.
