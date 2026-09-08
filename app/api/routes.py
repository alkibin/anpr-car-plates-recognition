from fastapi import APIRouter

router = APIRouter()


@router.get("/events")
async def list_events():
    return []


@router.get("/stats")
async def stats():
    return {"total": 0}
