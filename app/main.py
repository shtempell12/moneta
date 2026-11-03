from fastapi import FastAPI

from app.web.budget import router as budget_router
from app.web.entries import router as entries_router
from app.web.routes import router as web_router

app = FastAPI(title="Moneta")
app.include_router(web_router)
app.include_router(budget_router)
app.include_router(entries_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
