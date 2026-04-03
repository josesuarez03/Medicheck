import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers.inference import router as inference_router
from services.vector_store import VectorStore


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    vector_store = VectorStore()
    vector_store_ready = vector_store.ensure_ready()
    if not vector_store_ready:
        logger.warning("pgvector bootstrap did not complete during ai-service startup.")
    yield


app = FastAPI(
    title="Hipo AI Service",
    version="0.1.0",
    description="Bootstrap FastAPI del servicio de inferencia.",
    lifespan=lifespan,
)

app.include_router(inference_router)
