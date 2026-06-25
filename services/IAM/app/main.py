from typing import Any

from app.core.config import Settings
from fastapi import FastAPI

settings = Settings()

app = FastAPI(

    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    openapi_url=None if settings.environment == "production" else "/openapi.json"
)


@app.get("/")
def read_root() -> dict[str, Any]:
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None) -> dict[str, Any]:
    return {"item_id": item_id, "q": q}
