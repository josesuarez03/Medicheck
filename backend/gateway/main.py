import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.http_router import router as http_router
from routers.ws_router import router as ws_router


def _allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="Hipo Gateway",
    version="0.1.0",
    description="Bootstrap FastAPI del gateway para la futura modularizacion.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(http_router)
app.include_router(ws_router)
