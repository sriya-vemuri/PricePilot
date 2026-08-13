from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.api.errors import register_exception_handlers
from app.api.routers.analyses import router as analyses_router
from app.clients.tavily import TavilyClient
from app.config import Settings, get_settings
from app.db.session import create_db_engine


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = create_db_engine(settings=settings)
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    tavily_client = TavilyClient(settings)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.tavily_client = tavily_client
    try:
        yield
    finally:
        await tavily_client.aclose()
        engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    application = FastAPI(
        title="PricePilot API",
        version="0.1.0",
        lifespan=_lifespan,
    )
    application.state.settings = resolved
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(analyses_router, prefix="/api")

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
