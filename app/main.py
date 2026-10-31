from fastapi import FastAPI

from app.web.routes import router as web_router

app = FastAPI(title="Moneta")
app.include_router(web_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
