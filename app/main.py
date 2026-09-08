from fastapi import FastAPI

app = FastAPI(title="ANPR API")


@app.get("/health")
async def health():
    return {"status": "ok"}
