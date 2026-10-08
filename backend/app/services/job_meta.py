"""
Petit fichier meta.json écrit dans le dossier de chaque job, pour que la page
Historique puisse afficher un titre lisible (nom du fichier, lien YouTube...)
et la date de création, au lieu d'un simple identifiant.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


def write_job_meta(job_dir: Path, title: str, **details) -> None:
    meta = {"title": title, "created_at": datetime.now(timezone.utc).isoformat(), **details}
    (job_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
