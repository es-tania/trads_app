"""
Suivi générique de n'importe quel job (scraping, traduction, sous-titres) :
- GET  /jobs/{id}       -> statut courant + historique des logs
- GET  /jobs/{id}/result -> télécharge le fichier produit (si status=done)
- WS   /jobs/{id}/ws    -> logs en direct, ligne par ligne
"""
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.config import settings
from app.jobs.logging import JobLogger

router = APIRouter(prefix="/jobs", tags=["jobs"])


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


@router.websocket("/{job_id}/ws")
async def job_logs_ws(websocket: WebSocket, job_id: str):
    """Diffuse les logs en direct. Envoie d'abord l'historique, puis stream."""
    await websocket.accept()
    logger = JobLogger(job_id)

    for line in logger.get_logs():
        await websocket.send_text(line)

    status = logger.get_status()
    if status.get("status") in ("done", "error"):
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
            if "--- statut : done ---" in text or "--- statut : error ---" in text:
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
