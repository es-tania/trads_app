"""
Lance un worker qui exécute les jobs en tâche de fond (scraping, traduction,
sous-titres). À lancer dans un terminal séparé, en plus de `uvicorn` :

    python run_worker.py                 -> écoute fast + subtitles (simple, tout-en-un)
    python run_worker.py fast             -> écoute uniquement "fast" (scraping, traduction)
    python run_worker.py subtitles        -> écoute uniquement "subtitles" (Whisper, GPU)

Pour du vrai parallélisme (ex: scraper un script ET traduire un .docx en
même temps), lance plusieurs instances de ce script dans des terminaux
séparés — chacune tourne dans son propre process, donc les jobs s'exécutent
réellement en même temps, pas juste entrelacés. Recommandation :

    python run_worker.py fast         (terminal A)
    python run_worker.py fast         (terminal B, un 2e worker "fast" en plus)
    python run_worker.py subtitles    (terminal C — un seul, voir pourquoi ci-dessous)

Pourquoi un seul worker "subtitles" : Whisper utilise le GPU, et en faire
tourner deux en même temps risque de saturer la VRAM plutôt que d'aller plus
vite. Pour "fast" (scraping/traduction, réseau et CPU), il n'y a pas cette
limite : lance-en autant que tu veux.

⚠️ Pourquoi pas la commande `rq worker` standard ?
Elle repose sur os.fork() pour isoler chaque job et appliquer les timeouts,
ce qui n'existe pas sur Windows. On utilise donc SimpleWorker : les jobs
s'exécutent dans le même process, sans fork — un peu moins isolé (un crash
du worker durant un job ne se rattrape pas aussi proprement), mais largement
suffisant pour un usage personnel, et ça fonctionne identiquement sous
Windows, macOS et Linux.
"""
import sys

from rq import SimpleWorker

from app.jobs.queue import QUEUES, redis_conn

if __name__ == "__main__":
    requested = sys.argv[1:] or list(QUEUES.keys())
    unknown = [name for name in requested if name not in QUEUES]
    if unknown:
        raise SystemExit(f"File(s) inconnue(s) : {unknown} (attendu parmi {list(QUEUES.keys())})")

    queues = [QUEUES[name] for name in requested]
    worker = SimpleWorker(queues, connection=redis_conn)
    worker.work()
