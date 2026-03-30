from fastapi import FastAPI

from routers.http_router import router as http_router
from routers.ws_router import router as ws_router


app = FastAPI(
    title="Hipo Gateway",
    version="0.1.0",
    description="Bootstrap FastAPI del gateway para la futura modularizacion.",
)

app.include_router(http_router)
app.include_router(ws_router)
