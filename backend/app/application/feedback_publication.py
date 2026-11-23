"""维护人审核后原子发布反馈草稿、案例及版本，并向案例读者提供有限的实际反馈依据。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contracts.feedback_drafts import (
    FeedbackDraftEvidence,
    FeedbackDraftPublish,
    FeedbackDraftRead,
    PublishedFeedbackRead,
)
from ..contracts.responses import CaseRead, json_object
from ..domain.commands import CaseChanges, DraftContent
from ..domain.errors import BusinessError
from ..domain.policies import require_role, validate_case_change
from ..domain.types import Actor
from ..models import Case, CaseRevision, FeedbackDraft, Source
from .cases import apply_case_revision, owned_case
from .feedback_drafts import advance_draft, owned_draft
from .idempotency import once


def _new_case(db: Session, actor: Actor, item: FeedbackDraft, changes: CaseChanges) -> CaseRead:
    # 1. 原问题和实际反馈组成新的原始依据，AI 整理结果不冒充聊天或已执行事实。
    evidence = FeedbackDraftEvidence.model_validate(item.evidence)
    outcome = {"resolved": "已解决", "unresolved": "仍未解决", "not_applicable": "方案不适用"}[
        evidence.feedback.outcome
    ]
    source = Source(
        business=item.business,
        owner_id=item.owner_id,
        text=f"问题记录：{evidence.question.text}\n\n实际处理反馈（{outcome}）：\n{evidence.feedback.note}",
    )
    db.add(source)
    db.flush()
    # 2. 新案例关联本次反馈依据，验证人来自已经通过授权的实际审核主体。
    case = Case(
        **changes.model_dump(),
        business=item.business,
        source_id=source.id,
        owner_id=item.owner_id,
        rule_version=item.rule_version,
        verified_by=actor.id if changes.validity == "verified" else None,
    )
    db.add(case)
    db.flush()
    # 3. 初始案例快照与新材料留在同一发布事务，失败时整体回滚。
    result = CaseRead.model_validate(case)
    db.add(
        CaseRevision(case_id=case.id, version=1, snapshot=json_object(result), editor_id=actor.id)
    )
    return result


def _publish(
    db: Session, actor: Actor, item: FeedbackDraft, data: FeedbackDraftPublish
) -> FeedbackDraftRead:
    # 1. 只发布已提交的提案；有效性必须由维护人显式选择并通过既有业务规则。
    if item.status != "pending":
        raise BusinessError(
            "DRAFT_NOT_PENDING", "请先保存并提交人工确认，已发布草稿不能重复发布", 409
        )
    changes = CaseChanges(
        **DraftContent.model_validate(item.content).model_dump(),
        publication="published",
        validity=data.validity,
    )
    validate_case_change(actor, item.owner_id, "pending", changes)
    # 2. 先用版本条件认领草稿，再更新目标案例；任何冲突会回滚整个发布事务。
    advance_draft(db, actor, item, data.version, {"status": "published", "published_by": actor.id})
    if item.kind == "revise":
        if not item.target_case_id or item.target_version is None:
            raise BusinessError("DATA_INTEGRITY_ERROR", "修订草稿缺少目标版本", 500)
        target = owned_case(db, actor, item.target_case_id)
        if target.business != item.business or target.publication != "published":
            raise BusinessError("INVALID_TARGET", "目标案例已归档或不可修订，请重新选择", 409)
        if target.version != item.target_version:
            raise BusinessError(
                "TARGET_VERSION_CONFLICT", "目标案例已更新，请核对最新版本后重新提交", 409
            )
        try:
            case = apply_case_revision(
                db, actor, target.id, item.target_version, changes, item.rule_version
            )
        except BusinessError as error:
            # 目标在前置读取与条件写入之间变化时，同样引导核对目标，而非误报草稿冲突。
            if error.code == "VERSION_CONFLICT":
                raise BusinessError(
                    "TARGET_VERSION_CONFLICT", "目标案例已更新，请核对最新版本后重新提交", 409
                ) from None
            raise
    else:
        case = _new_case(db, actor, item, changes)
    # 3. 保存发布去向与版本，审计、案例、依据和幂等结果由外层共同提交。
    item.published_case_id = case.id
    item.published_case_version = case.version
    db.flush()
    return FeedbackDraftRead.model_validate(item)


def publish_draft(
    db: Session, actor: Actor, draft_id: str, data: FeedbackDraftPublish, key: str
) -> FeedbackDraftRead:
    """先复核维护人和草稿权限再处理幂等缓存，发布成功后不能被旧请求重复应用。"""
    require_role(actor, "maintainer")
    item = owned_draft(db, actor, draft_id)
    result = once(
        db,
        actor,
        key,
        f"feedback-publish-{draft_id}",
        json_object(data),
        FeedbackDraftRead,
        lambda: _publish(db, actor, item, data),
    )
    return FeedbackDraftRead.model_validate(owned_draft(db, actor, result.id))


def published_evidence(db: Session, actor: Actor, case_id: str) -> list[PublishedFeedbackRead]:
    """只返回当前可见案例采用的实际反馈，不扩大个人提问和草稿的读取权限。"""
    owned_case(db, actor, case_id)
    values: list[PublishedFeedbackRead] = []
    for item in db.scalars(
        select(FeedbackDraft)
        .where(
            FeedbackDraft.published_case_id == case_id,
            FeedbackDraft.business.in_(actor.businesses),
            FeedbackDraft.status == "published",
        )
        .order_by(FeedbackDraft.published_case_version, FeedbackDraft.id)
    ):
        evidence = FeedbackDraftEvidence.model_validate(item.evidence)
        if item.published_case_version is None or item.published_by is None:
            raise BusinessError("DATA_INTEGRITY_ERROR", "发布依据不完整，请联系维护人", 500)
        values.append(
            PublishedFeedbackRead(
                draft_id=item.id,
                question_text=evidence.question.text,
                outcome=evidence.feedback.outcome,
                note=evidence.feedback.note,
                question_source_id=item.question_source_id,
                case_version=item.published_case_version,
                rule_version=item.rule_version,
                model=item.model,
                published_by=item.published_by,
            )
        )
    return values
