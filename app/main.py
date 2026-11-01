from fastapi import FastAPI

app = FastAPI(title="Moneta")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
