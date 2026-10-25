from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from nextmove import __version__
from nextmove.api import api_router
from nextmove.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.settings = get_settings()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Toyota NextMove API",
        description="Personalized next-action recommendations for Toyota customers.",
        version=__version__,
        debug=settings.nextmove_debug,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix="/api/v1")
    frontend = Path(settings.nextmove_frontend_dir).resolve()
    bundled_frontend = Path(__file__).resolve().parents[3] / "dist"
    if not frontend.is_dir() and bundled_frontend.is_dir():
        frontend = bundled_frontend
    if frontend.is_dir():
        application.mount("/site", StaticFiles(directory=frontend, html=True), name="site")

        @application.get("/", include_in_schema=False)
        def homepage() -> RedirectResponse:
            return RedirectResponse("/site/index.html")

    return application


app = create_app()
