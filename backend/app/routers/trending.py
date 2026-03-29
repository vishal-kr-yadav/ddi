from fastapi import APIRouter
from app.mongo import get_trending, get_recent

router = APIRouter()


@router.get("/trending")
async def trending():
    return {"trending": await get_trending(5)}


@router.get("/recent")
async def recent():
    return {"recent": await get_recent(8)}
