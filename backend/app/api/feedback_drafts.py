"""提供本人反馈整理与同业务草稿审核协议，所有写入由应用用例控制权限和事务。"""

from fastapi import APIRouter

from ..application import feedback_drafts, feedback_generation, feedback_publication
from ..contracts.feedback_drafts import (
    FeedbackDraftList,
    FeedbackDraftPublish,
    FeedbackDraftRead,
    FeedbackDraftUpdate,
    PublishedFeedbackList,
)
from ..domain.commands import FeedbackDraftChanges
from ..domain.types import Business
from .dependencies import DB, CurrentActor, RequestKey

router = APIRouter(tags=["反馈案例草稿"])


@router.post(
    "/questions/{question_id}/feedback/{feedback_id}/draft",
    status_code=201,
    response_model=FeedbackDraftRead,
    operation_id="generateFeedbackDraft",
)
def generate_draft(
    question_id: str, feedback_id: str, actor: CurrentActor, db: DB, key: RequestKey
) -> FeedbackDraftRead:
    """本人主动整理；每份反馈只有一条草稿，重复请求打开当前草稿。"""
    return feedback_generation.generate_draft(db, actor, question_id, feedback_id, key)


@router.get("/feedback-drafts", response_model=FeedbackDraftList, operation_id="listFeedbackDrafts")
def list_drafts(business: Business, actor: CurrentActor, db: DB) -> FeedbackDraftList:
    """列出授权业务内可编辑或审核的反馈草稿，普通成员只看到本人记录。"""
    return FeedbackDraftList(feedback_drafts.list_drafts(db, actor, business))


@router.get(
    "/feedback-drafts/{draft_id}",
    response_model=FeedbackDraftRead,
    operation_id="readFeedbackDraft",
)
def read_draft(draft_id: str, actor: CurrentActor, db: DB) -> FeedbackDraftRead:
    """读取完整草稿及输入和修改历史，目标案例权限同时复核。"""
    return FeedbackDraftRead.model_validate(feedback_drafts.owned_draft(db, actor, draft_id))


@router.put(
    "/feedback-drafts/{draft_id}",
    response_model=FeedbackDraftRead,
    operation_id="updateFeedbackDraft",
)
def save_draft(
    draft_id: str, data: FeedbackDraftUpdate, actor: CurrentActor, db: DB
) -> FeedbackDraftRead:
    """保存编辑或提交审核，未发布的提案不会改变正式案例。"""
    changes = FeedbackDraftChanges.model_validate(data.model_dump(exclude={"version"}))
    return feedback_drafts.save_draft(db, actor, draft_id, data.version, changes)


@router.post(
    "/feedback-drafts/{draft_id}/publish",
    response_model=FeedbackDraftRead,
    operation_id="publishFeedbackDraft",
)
def publish_draft(
    draft_id: str, data: FeedbackDraftPublish, actor: CurrentActor, db: DB, key: RequestKey
) -> FeedbackDraftRead:
    """维护人显式确认有效性后，原子发布案例、版本及草稿去向。"""
    return feedback_publication.publish_draft(db, actor, draft_id, data, key)


@router.get(
    "/cases/{case_id}/feedback-evidence",
    response_model=PublishedFeedbackList,
    operation_id="listPublishedFeedbackEvidence",
)
def published_evidence(case_id: str, actor: CurrentActor, db: DB) -> PublishedFeedbackList:
    """案例读者只查看已采用反馈的有限依据，不获得完整私人草稿。"""
    return PublishedFeedbackList(feedback_publication.published_evidence(db, actor, case_id))
