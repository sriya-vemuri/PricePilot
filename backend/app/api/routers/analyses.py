from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_analysis_orchestrator, get_analysis_repository
from app.api.errors import AnalysisNotFoundError
from app.auth import AuthenticatedUser, get_current_user
from app.models.requests import CreateAnalysisRequest
from app.models.responses import AnalysisDetailResponse, AnalysisListResponse
from app.repositories.analysis_repo import AnalysisRepository
from app.services.analysis_orchestrator import AnalysisOrchestrator

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisDetailResponse, status_code=201)
async def create_analysis(
    payload: CreateAnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    orchestrator: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> AnalysisDetailResponse:
    return await orchestrator.create_analysis(payload, current_user.user_id)


@router.get("", response_model=AnalysisListResponse)
def list_analyses(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: AnalysisRepository = Depends(get_analysis_repository),
) -> AnalysisListResponse:
    return repo.list_analyses(current_user.user_id, limit=limit, offset=offset)


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis(
    analysis_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: AnalysisRepository = Depends(get_analysis_repository),
) -> AnalysisDetailResponse:
    result = repo.get_by_id(analysis_id, current_user.user_id)
    if result is None:
        raise AnalysisNotFoundError(analysis_id)
    return result
