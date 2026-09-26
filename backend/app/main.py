"""
API unique remplaçant n8n + les 4 scripts séparés.

Lancer en local :
    uvicorn app.main:app --reload --port 8000

Documentation interactive générée automatiquement : http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ocr, scraping, subtitles, translate

app = FastAPI(title="Trads LADS API", version="0.1.0")

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


@app.get("/health")
def health():
    return {"status": "ok"}
