from fastapi import APIRouter

router = APIRouter(
    prefix="/health",
    tags=["system"],
)


@router.get("")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }