import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import rou

logger = logging.getLogger("app.main")

def create_app() -> FastAPI:
    app = FastAPI(docs_url="/swagger",)

    app.add_middleware(
        CORSMiddleware,
        # allow_origins=settings.ALLOWED_ORIGINS,
        # allow_credentials=True,
        allow_origins=["*"],
        allow_credentials=False,  # MUST be False when origins="*"
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(rou)

    return app
