import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.mongo import init_mongo, close_mongo, get_client, get_device_usage
from app.routers import fact_check, trending

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DDI API...")
    await init_mongo()
    logger.info("Startup complete — ready to serve requests")
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


@app.get("/health", tags=["Health"])
async def health():
    mongo_ok = False
    try:
        client = get_client()
        if client:
            await client.admin.command("ping")
            mongo_ok = True
    except Exception:
        pass
    return {"status": "ok", "service": "DDI API v2.0", "mongo": mongo_ok}


@app.get("/api/v1/device-usage", tags=["Usage"])
async def device_usage(device_id: str):
    if not device_id.strip():
        return {"checks_used": 0, "checks_remaining": settings.DAILY_DEVICE_LIMIT, "limit": settings.DAILY_DEVICE_LIMIT}
    return await get_device_usage(device_id.strip())


# ── Serve frontend static files in production ─────────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
logger.info(f"Frontend dist path: {FRONTEND_DIST} (exists: {FRONTEND_DIST.is_dir()})")

if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        file = FRONTEND_DIST / full_path
        if file.is_file():
            return FileResponse(file)
        index = FRONTEND_DIST / "index.html"
        if index.is_file():
            return FileResponse(index)
        return {"error": "Frontend not built"}
