"""
Connexion Redis + files d'attente RQ, partagées entre l'API (publication des
jobs) et les workers (exécution).

Deux files séparées plutôt qu'une seule "default" :
- "fast" : scraping + traduction (réseau/CPU, légers, peuvent tourner
  plusieurs en parallèle sans souci) ;
- "subtitles" : génération de sous-titres (Whisper, utilise le GPU — en
  faire tourner deux en même temps risquerait de saturer la VRAM).

Un seul worker (SimpleWorker) ne traite qu'un job à la fois, quel que soit
le nombre de files qu'il écoute. Pour du vrai parallélisme (ex: scraper et
traduire en même temps), il faut lancer plusieurs *process* worker séparés
(voir run_worker.py) — les séparer par file permet de contrôler précisément
combien de jobs de chaque catégorie peuvent tourner en même temps.

⚠️ Windows : ne pas lancer le worker avec la commande `rq worker` standard,
elle repose sur os.fork() qui n'existe pas sur Windows. Utiliser
`python run_worker.py` à la racine de backend/ à la place (voir ce fichier).
"""
import redis
from rq import Queue

from app.config import settings

redis_conn = redis.from_url(settings.redis_url)

queue_fast = Queue("fast", connection=redis_conn)
queue_subtitles = Queue("subtitles", connection=redis_conn)

QUEUES = {"fast": queue_fast, "subtitles": queue_subtitles}
