"""从本人反馈整理一次可编辑草稿，模型调用后复核权限，唯一反馈约束保护并发重复生成。"""

from time import perf_counter

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..contracts.feedback_drafts import (
    FeedbackDraftEvidence,
    FeedbackDraftRead,
)
from ..contracts.responses import FeedbackRead, SourceRead, json_object
from ..domain.commands import DraftContent
from ..domain.errors import BusinessError
from ..domain.types import Actor
from ..models import Feedback, FeedbackDraft, timestamp
from ..provider import model_json
from .analysis import my_question, question_detail
from .feedback_drafts import history_entry, owned_draft
from .idempotency import once
from .identity import refresh_actor
from .materials import owned_source
from .model_settings import active_connection
from .rules import FEEDBACK_RULE, FEEDBACK_VERSION


def _evidence(
    db: Session, actor: Actor, question_id: str, feedback_id: str
) -> FeedbackDraftEvidence:
    detail = question_detail(db, actor, question_id)
    feedback = db.scalar(
        select(Feedback).where(Feedback.id == feedback_id, Feedback.question_id == question_id)
    )
    if not feedback:
        raise BusinessError("NOT_FOUND", "处理反馈不存在", 404)
    source = (
        owned_source(db, actor, detail.question.source_id) if detail.question.source_id else None
    )
    return FeedbackDraftEvidence(
        question=detail.question,
        feedback=FeedbackRead.model_validate(feedback),
        run=detail.run,
        source=SourceRead.model_validate(source) if source else None,
    )


def _generate(db: Session, actor: Actor, question_id: str, feedback_id: str) -> FeedbackDraftRead:
    # 1. 每份反馈只有一条草稿，重新打开不得覆盖已人工编辑或已发布的内容。
    existing = db.scalar(select(FeedbackDraft).where(FeedbackDraft.feedback_id == feedback_id))
    if existing:
        return FeedbackDraftRead.model_validate(owned_draft(db, actor, existing.id))
    evidence = _evidence(db, actor, question_id, feedback_id)
    started = perf_counter()
    content = DraftContent(
        title=" ".join(evidence.question.text.split())[:80],
        symptom=evidence.question.text,
        investigation=evidence.feedback.note,
    )
    connection = active_connection(db)
    # 2. 本地模式只预填问题与实际反馈，不把模型建议当作执行结果或验证依据。
    if connection:
        content = model_json(FEEDBACK_RULE, json_object(evidence), DraftContent, connection)
    # 3. 远端等待后复核本人问题、业务及材料访问权，撤权时不保存成功结果。
    actor = refresh_actor(db, actor)
    question = my_question(db, actor, question_id)
    if question.source_id:
        owned_source(db, actor, question.source_id)
    now = timestamp()
    item = FeedbackDraft(
        question_id=question_id,
        feedback_id=feedback_id,
        run_id=evidence.run.id,
        business=question.business,
        owner_id=actor.id,
        question_source_id=question.source_id,
        kind="create",
        status="draft",
        version=1,
        content=json_object(content),
        generated_content=json_object(content),
        evidence=json_object(evidence),
        rule_version=FEEDBACK_VERSION,
        model=connection.model if connection else "local-rules-v1",
        mode="model" if connection else "local_rules",
        duration_ms=int((perf_counter() - started) * 1000),
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.flush()
    item.history = [history_entry(item, actor)]
    return FeedbackDraftRead.model_validate(item)


def generate_draft(
    db: Session, actor: Actor, question_id: str, feedback_id: str, key: str
) -> FeedbackDraftRead:
    """本人主动生成；同键重放及不同键并发都返回已有草稿的当前版本。"""
    _evidence(db, actor, question_id, feedback_id)
    try:
        value = once(
            db,
            actor,
            key,
            "feedback-draft",
            {"feedback_id": feedback_id},
            FeedbackDraftRead,
            lambda: _generate(db, actor, question_id, feedback_id),
        )
    except IntegrityError:
        # 不同请求键同时生成同一反馈时，失败事务回滚后读取唯一约束的胜出记录。
        db.rollback()
        actor = refresh_actor(db, actor)
        my_question(db, actor, question_id)
        existing = db.scalar(select(FeedbackDraft).where(FeedbackDraft.feedback_id == feedback_id))
        if not existing:
            raise
        value = FeedbackDraftRead.model_validate(owned_draft(db, actor, existing.id))
    return FeedbackDraftRead.model_validate(owned_draft(db, refresh_actor(db, actor), value.id))
