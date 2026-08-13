from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.clients.tavily import TavilyClient
from app.config import Settings
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.market_cache_repo import MarketCacheRepository
from app.services.analysis_orchestrator import AnalysisOrchestrator
from app.services.market_research.service import MarketResearchService


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_analysis_repository(session: Session = Depends(get_db_session)) -> AnalysisRepository:
    return AnalysisRepository(session)


def get_market_cache_repository(session: Session = Depends(get_db_session)) -> MarketCacheRepository:
    return MarketCacheRepository(session)


def get_tavily_client(request: Request) -> TavilyClient:
    return request.app.state.tavily_client


def get_market_research_service(
    tavily_client: TavilyClient = Depends(get_tavily_client),
    cache_repo: MarketCacheRepository = Depends(get_market_cache_repository),
    settings: Settings = Depends(get_app_settings),
) -> MarketResearchService:
    return MarketResearchService(tavily_client, cache_repo=cache_repo, settings=settings)


def get_analysis_orchestrator(
    market_research: MarketResearchService = Depends(get_market_research_service),
    analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
) -> AnalysisOrchestrator:
    return AnalysisOrchestrator(market_research, analysis_repo)
