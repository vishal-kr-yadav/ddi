import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.mongo import init_mongo, close_mongo, _client
from app.routers import fact_check, trending, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_mongo()
    yield
    await close_mongo()


app = FastAPI(
    title="DDI - Data Driven Intelligence",
    description="AI-powered global fact-checking platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fact_check.router, prefix="/api/v1", tags=["Fact Check"])
app.include_router(trending.router,   prefix="/api/v1", tags=["Trending"])
app.include_router(users.router,     prefix="/api/v1", tags=["Users"])


@app.get("/health", tags=["Health"])
async def health():
    mongo_ok = False
    try:
        if _client:
            await _client.admin.command("ping")
            mongo_ok = True
    except Exception:
        pass
    return {"status": "ok", "service": "DDI API v2.0", "mongo": mongo_ok}


# ── Serve frontend static files in production ─────────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        file = FRONTEND_DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")
