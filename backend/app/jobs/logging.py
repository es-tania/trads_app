"""
Suivi d'un job en cours : statut + logs, stockés dans Redis.

- une liste Redis (`job:<id>:logs`) garde l'historique complet des lignes de
  log, pour qu'un client qui se connecte après coup (ou qui recharge la
  page) puisse tout revoir ;
- un canal pub/sub (`job:<id>:channel`) diffuse chaque nouvelle ligne en
  direct aux clients connectés via WebSocket ;
- un hash Redis (`job:<id>:meta`) garde le statut courant (queued / running /
  done / error / cancelled) et le résultat final (chemin du fichier à
  télécharger) ;
- une clé Redis (`job:<id>:cancel`) sert de demande d'arrêt coopérative : une
  tâche en cours la vérifie à intervalles réguliers et s'arrête proprement
  si elle est présente (voir app/jobs/tasks.py).

Tout expire au bout de 24h : pas besoin de nettoyage manuel pour un usage
personnel avec un volume de jobs modeste.
"""
import json
from datetime import datetime, timezone

from app.jobs.queue import redis_conn

_TTL_SECONDS = 60 * 60 * 24


class JobLogger:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.log_key = f"job:{job_id}:logs"
        self.meta_key = f"job:{job_id}:meta"
        self.channel = f"job:{job_id}:channel"
        self.cancel_key = f"job:{job_id}:cancel"

    def log(self, message: str) -> None:
        line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}"
        redis_conn.rpush(self.log_key, line)
        redis_conn.expire(self.log_key, _TTL_SECONDS)
        redis_conn.publish(self.channel, line)

    def set_status(self, status: str, **extra) -> None:
        """status : 'queued' | 'running' | 'done' | 'error' | 'cancelled'."""
        payload = {"status": status, **extra}
        redis_conn.hset(self.meta_key, mapping={k: json.dumps(v) for k, v in payload.items()})
        redis_conn.expire(self.meta_key, _TTL_SECONDS)
        self.log(f"--- statut : {status} ---")

    def get_status(self) -> dict:
        raw = redis_conn.hgetall(self.meta_key)
        return {k.decode(): json.loads(v) for k, v in raw.items()}

    def get_logs(self) -> list[str]:
        return [line.decode() for line in redis_conn.lrange(self.log_key, 0, -1)]

    def request_cancel(self) -> None:
        redis_conn.set(self.cancel_key, "1", ex=_TTL_SECONDS)

    def is_cancel_requested(self) -> bool:
        return redis_conn.exists(self.cancel_key) == 1
