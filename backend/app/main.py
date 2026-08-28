from fastapi import FastAPI


app = FastAPI(
    title="Bar Vision API",
    version="0.1.0",
)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}