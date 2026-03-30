from fastapi import FastAPI

from routers.triage import router as triage_router
from services.loader import load_knowledge_base


app = FastAPI(
    title="Hipo Expert Service",
    version="0.1.0",
    description="Servicio experto autónomo para triaje basado en reglas.",
)


@app.on_event("startup")
async def preload_rules() -> None:
    load_knowledge_base()


app.include_router(triage_router)
