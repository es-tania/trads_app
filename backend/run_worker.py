"""
Lance le worker qui exécute les jobs en tâche de fond (scraping, traduction,
sous-titres). À lancer dans un terminal séparé, en plus de `uvicorn` :

    python run_worker.py

⚠️ Pourquoi pas la commande `rq worker` standard ?
Elle repose sur os.fork() pour isoler chaque job et appliquer les timeouts,
ce qui n'existe pas sur Windows. On utilise donc SimpleWorker : les jobs
s'exécutent dans le même process, sans fork — un peu moins isolé (un crash
du worker durant un job ne se rattrape pas aussi proprement), mais largement
suffisant pour un usage personnel, et ça fonctionne identiquement sous
Windows, macOS et Linux.
"""
from rq import SimpleWorker

from app.jobs.queue import queue, redis_conn

if __name__ == "__main__":
    worker = SimpleWorker([queue], connection=redis_conn)
    worker.work()
