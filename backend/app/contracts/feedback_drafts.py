"""定义反馈整理、人工编辑、发布与来源追溯契约，不向普通案例读者公开私有运行上下文。"""

from pydantic import Field, RootModel

from ..domain.commands import Command, DraftContent, FeedbackDraftChanges
from ..domain.types import AnalysisMode, Business, ChangeKind, ChangeStatus, Outcome, Validity
from .responses import CaseRead, FeedbackRead, QuestionRead, ReadModel, RunRead, SourceRead


class FeedbackDraftUpdate(FeedbackDraftChanges):
    """带预期版本保存完整草稿，冲突时调用方保留输入。"""

    version: int = Field(ge=1, description="编辑时读取的草稿版本")


class FeedbackDraftPublish(Command):
    """维护人显式确认有效性后发布；问题已解决不能替代验证依据。"""

    version: int = Field(ge=1, description="审核时读取的草稿版本")
    validity: Validity = Field(description="人工确认的方案有效性，不从反馈状态推断")


class FeedbackDraftEvidence(ReadModel):
    """保存整理时的输入快照，运行建议与实际反馈分开表达。"""

    question: QuestionRead
    feedback: FeedbackRead
    run: RunRead
    source: SourceRead | None


class FeedbackDraftHistory(ReadModel):
    """每次保存与发布保留完整提案及操作主体，最初生成内容另外保留。"""

    version: int
    editor_id: str
    created_at: str
    status: ChangeStatus
    kind: ChangeKind
    content: DraftContent
    target_case_id: str | None
    target_version: int | None
    base_snapshot: CaseRead | None


class FeedbackDraftRead(ReadModel):
    """仅所有者与同业务处理角色可读的完整变更草稿，不代表正式案例。"""

    id: str
    question_id: str
    feedback_id: str
    run_id: str
    business: Business
    owner_id: str
    kind: ChangeKind
    status: ChangeStatus
    version: int
    target_case_id: str | None
    target_version: int | None
    base_snapshot: CaseRead | None
    content: DraftContent
    generated_content: DraftContent
    evidence: FeedbackDraftEvidence
    history: list[FeedbackDraftHistory]
    rule_version: str
    model: str
    mode: AnalysisMode
    duration_ms: int = Field(description="整理耗时，单位毫秒")
    published_case_id: str | None
    published_case_version: int | None
    published_by: str | None
    created_at: str
    updated_at: str


class FeedbackDraftList(RootModel[list[FeedbackDraftRead]]):
    """按业务及主体权限返回的反馈草稿，已发布项仍可追溯。"""


class PublishedFeedbackRead(ReadModel):
    """正式案例的反馈依据，不包含私人分析结果和未采用的人工草稿。"""

    draft_id: str
    question_text: str
    outcome: Outcome
    note: str
    question_source_id: str | None
    case_version: int
    rule_version: str
    model: str
    published_by: str


class PublishedFeedbackList(RootModel[list[PublishedFeedbackRead]]):
    """当前可见案例通过反馈新增或修订时留下的发布依据。"""
