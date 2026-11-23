"""维护反馈草稿授权、版本编辑和审计；正式案例的写入由发布用例单独负责。"""

from collections.abc import Mapping

from pydantic import JsonValue
from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from ..contracts.feedback_drafts import FeedbackDraftHistory, FeedbackDraftRead
from ..contracts.responses import CaseRead, json_object
from ..domain.commands import FeedbackDraftChanges
from ..domain.errors import BusinessError
from ..domain.policies import allow_business
from ..domain.types import Actor, Business
from ..models import Case, FeedbackDraft, timestamp
from .cases import owned_case


def visible_drafts(actor: Actor) -> Select[FeedbackDraft]:
    """列表、详情和待确认计数共用存储过滤，普通成员不能借统计推断他人草稿。"""
    statement = select(FeedbackDraft).where(FeedbackDraft.business.in_(actor.businesses))
    if actor.role == "member":
        statement = statement.outerjoin(Case, Case.id == FeedbackDraft.target_case_id).where(
            FeedbackDraft.owner_id == actor.id,
            (FeedbackDraft.target_case_id.is_(None))
            | (
                (Case.business.in_(actor.businesses))
                & ((Case.publication == "published") | (Case.owner_id == actor.id))
            ),
        )
    return statement


def owned_draft(db: Session, actor: Actor, draft_id: str) -> FeedbackDraft:
    """普通成员只能读取本人草稿，处理角色仅在授权业务内协作审核。"""
    statement = visible_drafts(actor).where(FeedbackDraft.id == draft_id)
    item = db.scalar(statement.execution_options(populate_existing=True))
    if not item:
        raise BusinessError("NOT_FOUND", "反馈草稿不存在", 404)
    if item.target_case_id:
        owned_case(db, actor, item.target_case_id)
    return item


def list_drafts(db: Session, actor: Actor, business: Business) -> list[FeedbackDraftRead]:
    """列出当前业务的可见提案，未提交项也保留供所有者继续编辑。"""
    allow_business(actor, business)
    statement = visible_drafts(actor).where(FeedbackDraft.business == business)
    return [
        FeedbackDraftRead.model_validate(item)
        for item in db.scalars(
            statement.order_by(FeedbackDraft.updated_at.desc(), FeedbackDraft.id)
        )
    ]


def history_entry(item: FeedbackDraft, actor: Actor) -> dict[str, JsonValue]:
    """由服务端生成操作主体与版本快照，调用方不能伪造审计。"""
    return json_object(
        FeedbackDraftHistory.model_validate(
            {
                "version": item.version,
                "editor_id": actor.id,
                "created_at": item.updated_at,
                "status": item.status,
                "kind": item.kind,
                "content": item.content,
                "target_case_id": item.target_case_id,
                "target_version": item.target_version,
                "base_snapshot": item.base_snapshot,
            }
        )
    )


def advance_draft(
    db: Session, actor: Actor, item: FeedbackDraft, version: int, values: Mapping[str, object]
) -> None:
    """以草稿版本认领写入并追加快照，外层事务决定与发布结果共同提交或回滚。"""
    # 1. 用当前业务和预期版本限制写入，避免两个审核请求同时认领同一草稿。
    result = db.execute(
        update(FeedbackDraft)
        .where(
            FeedbackDraft.id == item.id,
            FeedbackDraft.business.in_(actor.businesses),
            FeedbackDraft.version == version,
            FeedbackDraft.status != "published",
        )
        .values(**values, version=version + 1, updated_at=timestamp())
        .returning(FeedbackDraft.id),
        execution_options={"synchronize_session": False},
    )
    if result.scalar_one_or_none() is None:
        db.rollback()
        raise BusinessError("VERSION_CONFLICT", "草稿已更新或已发布，请读取最新草稿后核对", 409)
    db.refresh(item)
    # 2. 为已认领的新版本追加完整快照，随外层业务事务共同提交。
    item.history = [*item.history, history_entry(item, actor)]


def save_draft(
    db: Session, actor: Actor, draft_id: str, version: int, changes: FeedbackDraftChanges
) -> FeedbackDraftRead:
    """保存或提交人工确认，不修改正式案例；目标版本过期时保留服务端旧草稿。"""
    # 1. 草稿归属与目标案例均按当前权限检查，不信任客户端业务和目标快照。
    item = owned_draft(db, actor, draft_id)
    base: CaseRead | None = None
    if changes.target_case_id:
        target = owned_case(db, actor, changes.target_case_id)
        if target.business != item.business:
            raise BusinessError("INVALID_INPUT", "修订目标必须属于同一业务", 422)
        if target.publication != "published":
            raise BusinessError("INVALID_TARGET", "请选择已发布的案例进行修订", 409)
        if target.version != changes.target_version:
            raise BusinessError("TARGET_VERSION_CONFLICT", "目标案例已更新，请核对最新版本", 409)
        base = CaseRead.model_validate(target)
    # 2. 版本条件与审计共同写入，已解决反馈不会在此设置验证或发布状态。
    values = json_object(changes)
    values["base_snapshot"] = json_object(base) if base else None
    advance_draft(db, actor, item, version, values)
    db.commit()
    return FeedbackDraftRead.model_validate(item)
