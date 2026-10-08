"""
Suivi générique de n'importe quel job (scraping, traduction, sous-titres) :
- GET  /jobs/{id}        -> statut courant + historique des logs
- GET  /jobs/{id}/result -> télécharge le fichier produit (si status=done)
- POST /jobs/{id}/cancel -> demande l'arrêt du job
- WS   /jobs/{id}/ws     -> logs en direct, ligne par ligne
"""
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.config import settings
from app.jobs.logging import JobLogger
from app.jobs.queue import redis_conn

router = APIRouter(prefix="/jobs", tags=["jobs"])

_TERMINAL_STATUSES = ("done", "error", "cancelled")


@router.get("/{job_id}")
def get_job_status(job_id: str):
    logger = JobLogger(job_id)
    status = logger.get_status()
    if not status:
        raise HTTPException(status_code=404, detail="Job introuvable (ou expiré après 24h)")
    return {"job_id": job_id, "logs": logger.get_logs(), **status}


@router.get("/{job_id}/result")
def get_job_result(job_id: str):
    logger = JobLogger(job_id)
    status = logger.get_status()
    if not status:
        raise HTTPException(status_code=404, detail="Job introuvable (ou expiré après 24h)")
    if status.get("status") != "done":
        raise HTTPException(status_code=409, detail=f"Job pas encore terminé (statut : {status.get('status')})")

    result_path = status.get("result_path")
    if not result_path:
        raise HTTPException(status_code=404, detail="Aucun fichier de résultat pour ce job")

    return FileResponse(result_path, filename=status.get("result_filename", "resultat"))


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    """
    Demande l'arrêt d'un job. Deux cas :
    - encore en file d'attente (pas démarré) -> annulé immédiatement via RQ ;
    - déjà en cours -> flag coopératif, la tâche s'arrête à son prochain
      point de contrôle (voir app/jobs/tasks.py). Pour le scraping et la
      traduction, un unique appel réseau/CLI bloquant est en cours : l'arrêt
      n'est effectif qu'une fois cet appel terminé. Pour les sous-titres,
      l'arrêt est quasi immédiat (le sous-processus Whisper est tué).
    """
    logger = JobLogger(job_id)
    status = logger.get_status()
    if not status:
        raise HTTPException(status_code=404, detail="Job introuvable (ou expiré après 24h)")
    if status.get("status") in _TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail=f"Job déjà terminé (statut : {status.get('status')})")

    try:
        Job.fetch(job_id, connection=redis_conn).cancel()
    except NoSuchJobError:
        pass  # déjà retiré de la file par RQ, ou déjà en cours d'exécution

    logger.request_cancel()
    logger.log("Arrêt demandé par l'utilisateur...")
    return {"ok": True}


@router.websocket("/{job_id}/ws")
async def job_logs_ws(websocket: WebSocket, job_id: str):
    """Diffuse les logs en direct. Envoie d'abord l'historique, puis stream."""
    await websocket.accept()
    logger = JobLogger(job_id)

    for line in logger.get_logs():
        await websocket.send_text(line)

    status = logger.get_status()
    if status.get("status") in _TERMINAL_STATUSES:
        await websocket.close()
        return

    conn = aioredis.from_url(settings.redis_url)
    pubsub = conn.pubsub()
    await pubsub.subscribe(logger.channel)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            text = message["data"].decode()
            await websocket.send_text(text)
            if any(f"--- statut : {s} ---" in text for s in _TERMINAL_STATUSES):
                break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(logger.channel)
        await conn.close()
        try:
            await websocket.close()
        except RuntimeError:
            pass  # déjà fermée côté client
