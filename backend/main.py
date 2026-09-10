from fastapi import FastAPI

app = FastAPI(title="Indonesia Economic Intelligence API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
