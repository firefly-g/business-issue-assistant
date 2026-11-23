"""提供健康状态和当前身份统计，统计查询统一限制授权范围。"""

from fastapi import APIRouter
from sqlalchemy import func, select

from ..application.feedback_drafts import visible_drafts
from ..application.model_settings import runtime_mode
from ..contracts.responses import HealthRead, OverviewRead
from ..models import Case, FeedbackDraft, Question
from .dependencies import DB, CurrentActor

router = APIRouter(tags=["工作台"])


@router.get("/health", response_model=HealthRead, operation_id="health")
def health(db: DB) -> HealthRead:
    """执行轻量数据库探测，响应不暴露连接信息。"""
    db.execute(select(1))
    return HealthRead(status="ok", analysis_mode=runtime_mode(db))


@router.get("/overview", response_model=OverviewRead, operation_id="overview")
def overview(actor: CurrentActor, db: DB) -> OverviewRead:
    """只统计可访问案例、反馈草稿及本人提问，待确认徽标沿用实际列表权限。"""
    statement = select(Case).where(Case.business.in_(actor.businesses))
    if actor.role == "member":
        statement = statement.where((Case.publication == "published") | (Case.owner_id == actor.id))
    items = list(db.scalars(statement))
    feedback_pending = (
        db.scalar(
            select(func.count()).select_from(
                visible_drafts(actor).where(FeedbackDraft.status == "pending").subquery()
            )
        )
        or 0
    )
    questions = (
        db.scalar(
            select(func.count())
            .select_from(Question)
            .where(Question.owner_id == actor.id, Question.business.in_(actor.businesses))
        )
        or 0
    )
    return OverviewRead(
        analysis_mode=runtime_mode(db),
        published=sum(item.publication == "published" for item in items),
        verified=sum(
            item.publication == "published" and item.validity == "verified" for item in items
        ),
        pending=sum(item.publication == "pending" for item in items) + feedback_pending,
        questions=questions,
    )
