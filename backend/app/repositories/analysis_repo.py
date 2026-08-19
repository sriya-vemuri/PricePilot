from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.db.tables import Analysis
from app.models.responses import AnalysisDetailResponse, AnalysisListResponse, AnalysisSummaryResponse
from app.repositories.errors import DatabaseError
from app.repositories.mappers import analysis_from_create, to_analysis_detail, to_analysis_summary
from app.repositories.schemas import AnalysisCreate


class AnalysisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_analysis(self, payload: AnalysisCreate) -> AnalysisDetailResponse:
        try:
            analysis = analysis_from_create(payload)
            self.session.add(analysis)
            self.session.commit()
            self.session.refresh(analysis)
            return to_analysis_detail(analysis)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseError("Failed to save analysis") from exc
        except Exception:
            self.session.rollback()
            raise

    def get_by_id(self, analysis_id: UUID, user_id: str) -> AnalysisDetailResponse | None:
        try:
            stmt = (
                select(Analysis)
                .options(selectinload(Analysis.market_data))
                .where(Analysis.id == analysis_id, Analysis.user_id == user_id)
            )
            row = self.session.scalar(stmt)
            if row is None:
                return None
            return to_analysis_detail(row)
        except SQLAlchemyError as exc:
            raise DatabaseError("Failed to load analysis") from exc

    def list_analyses(self, user_id: str, *, limit: int = 50, offset: int = 0) -> AnalysisListResponse:
        try:
            owner = Analysis.user_id == user_id
            total = self.session.scalar(select(func.count()).select_from(Analysis).where(owner)) or 0
            stmt = (
                select(Analysis)
                .options(selectinload(Analysis.market_data))
                .where(owner)
                .order_by(Analysis.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            rows = self.session.scalars(stmt).all()
            items = [to_analysis_summary(row) for row in rows]
            return AnalysisListResponse(items=items, total=total, limit=limit, offset=offset)
        except SQLAlchemyError as exc:
            raise DatabaseError("Failed to list analyses") from exc

    def delete_for_user(self, analysis_id: UUID, user_id: str) -> bool:
        try:
            stmt = select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
            row = self.session.scalar(stmt)
            if row is None:
                return False
            self.session.delete(row)
            self.session.commit()
            return True
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseError("Failed to delete analysis") from exc
        except Exception:
            self.session.rollback()
            raise
