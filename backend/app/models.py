"""定义用户、原始材料、案例版本与分析运行的关系型存储，使用稳定编号保留追溯关系。"""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import JsonValue
from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .domain.types import (
    AnalysisMode,
    Business,
    ChangeKind,
    ChangeStatus,
    Outcome,
    Progress,
    Publication,
    Role,
    Validity,
)


def identifier() -> str:
    """生成可跨材料、案例和运行引用的稳定随机编号。"""
    return str(uuid4())


def timestamp() -> str:
    """以带 UTC 时区的 ISO 8601 字符串记录业务时间。"""
    return datetime.now(UTC).isoformat()


class User(Base):
    """保存账号、角色和可访问业务，公开响应排除口令摘要。"""

    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[Role] = mapped_column(String(20), default="member")
    businesses: Mapped[list[Business]] = mapped_column(JSON, default=list)
    password_hash: Mapped[str] = mapped_column(Text)


class LoginSession(Base):
    """保存会话令牌摘要与到期时间，不保存可直接登录的原始令牌。"""

    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[float]


class ModelProfile(Base):
    """保存可选择的模型连接，API 密钥与运行快照同样只保存密文。"""

    __tablename__ = "model_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    address: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(200))
    encrypted_key: Mapped[str] = mapped_column(Text)


class ModelSettings(Base):
    """保存单一生效配置及版本，旧接口仍可读取最后一次启用的连接快照。"""

    __tablename__ = "model_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_model_settings_singleton"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int]
    mode: Mapped[AnalysisMode] = mapped_column(String(20))
    address: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(200))
    encrypted_key: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[str] = mapped_column(String(36))
    updated_at: Mapped[str] = mapped_column(String(40))
    profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("model_profiles.id", name="fk_model_settings_profile")
    )


class Source(Base):
    """保留不可变原始文本及可选附件，材料读取继承业务授权。"""

    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    business: Mapped[Business] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    attachment_name: Mapped[str | None] = mapped_column(String(255))
    attachment_path: Mapped[str | None] = mapped_column(Text)
    attachment_type: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    version: Mapped[int] = mapped_column(default=1)


class Case(Base):
    """独立保存发布和验证状态，人工编辑通过版本号检测并发冲突。"""

    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    title: Mapped[str] = mapped_column(String(160))
    business: Mapped[Business] = mapped_column(String(80))
    symptom: Mapped[str] = mapped_column(Text)
    conditions: Mapped[str] = mapped_column(Text, default="")
    investigation: Mapped[str] = mapped_column(Text, default="")
    cause: Mapped[str] = mapped_column(Text, default="")
    solution: Mapped[str] = mapped_column(Text, default="")
    verification: Mapped[str] = mapped_column(Text, default="")
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    publication: Mapped[Publication] = mapped_column(String(20), default="draft")
    validity: Mapped[Validity] = mapped_column(String(20), default="unverified")
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    rule_version: Mapped[str] = mapped_column(
        String(80), default="manual-v1", server_default="manual-v1"
    )
    is_demo: Mapped[bool] = mapped_column(default=False)


class CaseRevision(Base):
    """保存案例每个版本的完整快照与编辑主体，供历史追溯。"""

    __tablename__ = "case_revisions"
    __table_args__ = (UniqueConstraint("case_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    version: Mapped[int]
    snapshot: Mapped[dict[str, JsonValue]] = mapped_column(JSON)
    editor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Question(Base):
    """独立保存用户提问与处理进度，不因提问自动创建正式案例。"""

    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    text: Mapped[str] = mapped_column(Text)
    business: Mapped[Business] = mapped_column(String(80))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    progress: Mapped[Progress] = mapped_column(String(20), default="processing")
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class AnalysisRun(Base):
    """保存本次规则、模型与引用快照，使回答能够定位到当时依据。"""

    __tablename__ = "analysis_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    rule_version: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    result: Mapped[dict[str, JsonValue]] = mapped_column(JSON)
    duration_ms: Mapped[int]
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class Feedback(Base):
    """保留处理反馈的追加记录，单次失败不自动改变案例有效性。"""

    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    outcome: Mapped[Outcome] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)


class WriteRequest(Base):
    """与业务事务共同保存幂等键及结果，拒绝相同键绑定不同内容。"""

    __tablename__ = "write_requests"
    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict[str, JsonValue]] = mapped_column(JSON)


class FeedbackDraft(Base):
    """每份反馈最多整理一次；修订提案独立保存，发布事务才更新正式案例。"""

    __tablename__ = "feedback_drafts"
    __table_args__ = (UniqueConstraint("feedback_id", name="uq_feedback_drafts_feedback"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    feedback_id: Mapped[str] = mapped_column(ForeignKey("feedback.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"))
    business: Mapped[Business] = mapped_column(String(80))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    # 原始图片仍保存于原材料；只有发布成功后才通过案例关系授予同业务读者访问权。
    question_source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"))
    kind: Mapped[ChangeKind] = mapped_column(String(20), default="create")
    status: Mapped[ChangeStatus] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(default=1)
    target_case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"))
    target_version: Mapped[int | None]
    # 保存当前人工核对的基准，最初生成内容另存；历史快照保留每次基准与提案。
    base_snapshot: Mapped[dict[str, JsonValue] | None] = mapped_column(JSON)
    content: Mapped[dict[str, JsonValue]] = mapped_column(JSON)
    generated_content: Mapped[dict[str, JsonValue]] = mapped_column(JSON)
    evidence: Mapped[dict[str, JsonValue]] = mapped_column(JSON)
    history: Mapped[list[dict[str, JsonValue]]] = mapped_column(JSON, default=list)
    rule_version: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(200))
    mode: Mapped[AnalysisMode] = mapped_column(String(20))
    duration_ms: Mapped[int]
    published_case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"))
    published_case_version: Mapped[int | None]
    published_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(String(40), default=timestamp)
    updated_at: Mapped[str] = mapped_column(String(40), default=timestamp)
