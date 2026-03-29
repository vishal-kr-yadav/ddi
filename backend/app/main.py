import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.mongo import init_mongo, close_mongo
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
    return {"status": "ok", "service": "DDI API v2.0"}
