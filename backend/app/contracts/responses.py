"""声明响应安全投影和历史快照结构，避免 ORM 或文件路径直接进入 HTTP。"""

from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel, TypeAdapter

from ..domain.commands import DraftContent
from ..domain.types import AnalysisMode, Business, Outcome, Progress, Publication, Role, Validity


class ReadModel(BaseModel):
    """允许从已加载字段投影，响应字段以声明契约为准。"""

    model_config = ConfigDict(from_attributes=True)


class UserRead(ReadModel):
    """公开身份，永不返回口令摘要及会话令牌。"""

    id: str
    email: str
    name: str
    role: Role
    businesses: list[Business]


class SourceRead(ReadModel):
    """材料安全投影，附件通过授权下载接口读取。"""

    id: str
    business: Business
    text: str
    owner_id: str
    version: int
    created_at: str = Field(description="UTC 时区的 ISO 8601 时间")
    attachment_name: str | None
    attachment_type: str | None


class CaseRead(ReadModel):
    """案例事实与状态，历史记录缺少规则版本时保留手动录入语义。"""

    id: str
    title: str
    business: Business
    symptom: str
    conditions: str
    investigation: str
    cause: str
    solution: str
    verification: str
    verified_by: str | None
    publication: Publication
    validity: Validity
    source_id: str
    owner_id: str
    version: int
    created_at: str = Field(description="UTC 时区的 ISO 8601 时间")
    updated_at: str = Field(description="UTC 时区的 ISO 8601 时间")
    rule_version: str = Field(default="manual-v1", description="旧快照省略时表示手动录入")
    is_demo: bool


class CitationRead(CaseRead):
    """本次分析引用的案例快照，并标记当前版本是否仍可使用。"""

    source_version: int = Field(description="分析时读取的原始材料版本")
    currently_available: bool = Field(default=True, description="当前权限、状态和版本均一致时为真")


class RevisionRead(ReadModel):
    """版本快照与编辑人信息，用于追溯当时的确认内容。"""

    id: str
    case_id: str
    version: int
    snapshot: CaseRead
    editor_id: str
    created_at: str


class QuestionRead(ReadModel):
    """个人提问及实际处理进度，与案例发布和有效性独立。"""

    id: str
    text: str
    business: Business
    source_id: str | None
    owner_id: str
    progress: Progress
    created_at: str


class AnalysisResult(BaseModel):
    """持久化分析结果，引用仅来自后台授权检索。"""

    summary: str
    steps: list[str]
    missing: list[str]
    citations: list[CitationRead]
    reply: str
    mode: AnalysisMode
    notice: str


class RunRead(ReadModel):
    """模型、规则及耗时记录，耗时单位为毫秒。"""

    id: str
    question_id: str
    rule_version: str
    model: str
    result: AnalysisResult
    duration_ms: int = Field(description="分析耗时，单位毫秒")
    created_at: str


class FeedbackRead(ReadModel):
    """追加式实际反馈，重复请求只保留一次已提交结果。"""

    id: str
    question_id: str
    author_id: str
    outcome: Outcome
    note: str
    created_at: str


class AnalysisRead(BaseModel):
    """提问与运行结果组合，历史详情可追加反馈记录。"""

    question: QuestionRead
    run: RunRead
    feedback: list[FeedbackRead] = Field(
        default_factory=list, description="新增分析时为空，详情附带历史反馈"
    )


class DraftPreview(DraftContent):
    """草稿预览未写入案例，也不代表方案已经验证。"""

    rule_version: str
    mode: AnalysisMode
    similar: list[CaseRead]


class OverviewRead(BaseModel):
    """当前可见范围的统计值，普通成员只计入公开或本人案例。"""

    analysis_mode: AnalysisMode
    published: int
    verified: int
    pending: int
    questions: int


class HealthRead(BaseModel):
    """服务与数据库健康状态，不包含部署细节。"""

    status: str
    analysis_mode: AnalysisMode


class ModelSettingsRead(BaseModel):
    """维护人可见的团队配置，密钥只显示是否已设置。"""

    mode: AnalysisMode
    address: str
    model: str
    has_api_key: bool
    version: int


class ModelCatalogRead(BaseModel):
    """供应商公开给当前凭证的模型标识，实际对话兼容性通过试连确认。"""

    models: list[str]


class ModelProfileRead(BaseModel):
    """单套连接的安全视图，密钥只显示配置状态。"""

    id: str
    address: str
    model: str
    has_api_key: bool


class ModelLibraryRead(BaseModel):
    """团队连接列表和唯一启用项，版本用于拒绝过期保存或切换。"""

    mode: AnalysisMode
    active_profile_id: str | None
    version: int
    profiles: list[ModelProfileRead]


class ModelTestRead(BaseModel):
    """测试通过后签发短期凭证，保存时绑定账号、参数与配置版本。"""

    test_token: str


class ErrorRead(BaseModel):
    """稳定错误契约，detail 保留旧客户端的可展示消息。"""

    code: str
    message: str
    detail: str
    request_id: str


class CaseList(RootModel[list[CaseRead]]):
    """保持既有列表数组响应，前端使用同名根 Schema 进行校验。"""


class QuestionList(RootModel[list[QuestionRead]]):
    """当前账号的提问数组，不扩大维护人的个人记录权限。"""


class RevisionList(RootModel[list[RevisionRead]]):
    """按版本倒序返回历史快照数组。"""


def json_object(value: BaseModel) -> dict[str, JsonValue]:
    """在序列化边界验证 JSON 对象，避免任意 Python 对象进入持久化字段。"""
    return TypeAdapter(dict[str, JsonValue]).validate_python(value.model_dump(mode="json"))
