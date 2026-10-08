"""
API unique remplaçant n8n + les 4 scripts séparés.

Lancer en local (3 process séparés, voir README) :
    1. docker compose up -d flaresolverr redis
    2. uvicorn app.main:app --reload --port 8000
    3. python run_worker.py

Documentation interactive générée automatiquement : http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import jobs, ocr, scraping, storage, subtitles, translate

app = FastAPI(title="Trads LADS API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scraping.router)
app.include_router(translate.router)
app.include_router(ocr.router)
app.include_router(subtitles.router)
app.include_router(jobs.router)
app.include_router(storage.router)


@app.get("/health")
def health():
    return {"status": "ok"}
