"""维护原始材料与本地附件，材料不可原地改写，失败清理本次文件。"""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..contracts.responses import SourceRead
from ..domain.errors import BusinessError
from ..domain.policies import allow_business
from ..domain.types import Actor, Business
from ..models import Case, FeedbackDraft, Source, identifier

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def owned_source(db: Session, actor: Actor, source_id: str) -> Source:
    """核对业务范围与材料发布关系，普通成员只能查看本人或已发布案例的原文。"""
    statement = select(Source).where(Source.id == source_id, Source.business.in_(actor.businesses))
    if actor.role == "member":
        # 在数据库中先过滤可见范围，未授权时不加载原文，也不暴露目标是否存在。
        published = (
            select(Case.id)
            .where(
                Case.source_id == Source.id,
                Case.business == Source.business,
                Case.publication == "published",
            )
            .exists()
        )
        # 反馈草稿发布后，原问题截图成为该案例的补充依据；归档案例会撤回这条共享关系。
        feedback_published = (
            select(FeedbackDraft.id)
            .join(Case, Case.id == FeedbackDraft.published_case_id)
            .where(
                FeedbackDraft.question_source_id == Source.id,
                FeedbackDraft.business == Source.business,
                FeedbackDraft.status == "published",
                Case.business == Source.business,
                Case.publication == "published",
            )
            .exists()
        )
        statement = statement.where((Source.owner_id == actor.id) | published | feedback_published)
    source = db.scalar(statement)
    if not source:
        raise BusinessError("NOT_FOUND", "原始材料不存在", 404)
    return source


def image_type(content: bytes) -> str:
    """校验图片字节签名和大小，拒绝伪装成图片的可执行网页内容。"""
    if len(content) > MAX_IMAGE_BYTES:
        raise BusinessError("UPLOAD_TOO_LARGE", "图片不能超过 5 MB", 413)
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    raise BusinessError("INVALID_IMAGE", "请上传 PNG、JPEG 或 WebP 图片", 422)


def create_source(
    db: Session,
    actor: Actor,
    business: Business,
    text: str,
    filename: str | None,
    content: bytes | None,
) -> SourceRead:
    """授权后保存不可变材料，文件与数据库无法共用事务，失败时补偿删除新文件。"""
    # 1. 校验业务与材料内容，附件类型不信任客户端声明。
    allow_business(actor, business)
    if not text.strip():
        raise BusinessError("INVALID_INPUT", "请填写原始材料或截图背景说明", 422)
    path: Path | None = None
    media_type = image_type(content) if content is not None else None
    # 2. 使用服务端生成的文件名，上传名称只作为展示信息保留。
    if content is not None:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        path = settings.upload_dir / identifier()
        path.write_bytes(content)
    item = Source(
        business=business,
        text=text.strip(),
        owner_id=actor.id,
        attachment_name=Path(filename or "截图").name[:255] if content is not None else None,
        attachment_path=str(path) if path else None,
        attachment_type=media_type,
    )
    # 3. 事务失败时移除尚未关联成功的文件，不删除历史材料。
    try:
        db.add(item)
        db.commit()
    except Exception:
        db.rollback()
        if path:
            path.unlink(missing_ok=True)
        raise
    return SourceRead.model_validate(item)


def attachment(db: Session, actor: Actor, source_id: str) -> tuple[Path, str]:
    """按材料权限定位文件，路径不进入公开响应。"""
    item = owned_source(db, actor, source_id)
    if not item.attachment_path or not Path(item.attachment_path).is_file():
        raise BusinessError("NOT_FOUND", "附件不存在", 404)
    return Path(item.attachment_path), item.attachment_type or "application/octet-stream"
