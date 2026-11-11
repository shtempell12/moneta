from fastapi import FastAPI

from app.web.budget import router as budget_router
from app.web.entries import router as entries_router
from app.web.goals import router as goals_router
from app.web.onboarding import router as onboarding_router
from app.web.plan import router as plan_router
from app.web.routes import router as web_router

app = FastAPI(title="Moneta")
app.include_router(web_router)
app.include_router(budget_router)
app.include_router(entries_router)
app.include_router(plan_router)
app.include_router(goals_router)
app.include_router(onboarding_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
