"""
Connexion Redis + file d'attente RQ, partagées entre l'API (publication des
jobs) et le worker (exécution).

⚠️ Windows : ne pas lancer le worker avec la commande `rq worker` standard,
elle repose sur os.fork() qui n'existe pas sur Windows. Utiliser
`python run_worker.py` à la racine de backend/ à la place (voir ce fichier).
"""
import redis
from rq import Queue

from app.config import settings

redis_conn = redis.from_url(settings.redis_url)
queue = Queue("default", connection=redis_conn)
