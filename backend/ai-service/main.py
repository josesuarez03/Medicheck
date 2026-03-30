from fastapi import FastAPI

from routers.inference import router as inference_router


app = FastAPI(
    title="Hipo AI Service",
    version="0.1.0",
    description="Bootstrap FastAPI del servicio de inferencia.",
)

app.include_router(inference_router)
