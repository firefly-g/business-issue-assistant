"""维护案例访问、关键词排序及人工确认，写用例持有事务与版本条件。"""

import re

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..contracts.responses import CaseRead, DraftPreview, RevisionRead, json_object
from ..domain.commands import CaseChanges, DraftContent
from ..domain.errors import BusinessError
from ..domain.policies import allow_business, validate_case_change
from ..domain.types import Actor, Business
from ..models import Case, CaseRevision, Source, timestamp
from ..provider import model_json
from .idempotency import once
from .identity import refresh_actor
from .materials import owned_source
from .model_settings import active_connection
from .rules import INTAKE_RULE, INTAKE_VERSION


def owned_case(db: Session, actor: Actor, case_id: str) -> Case:
    """定位授权业务内案例，未公开草稿额外检查所有者和处理角色。"""
    statement = select(Case).where(Case.id == case_id, Case.business.in_(actor.businesses))
    if actor.role == "member":
        statement = statement.where((Case.publication == "published") | (Case.owner_id == actor.id))
    item = db.scalar(statement)
    if not item:
        raise BusinessError("NOT_FOUND", "案例不存在", 404)
    return item


def terms(text: str) -> set[str]:
    """中文按相邻双字召回，错误码保留完整词，排序分数不表示置信度。"""
    output = set(re.findall(r"[a-z0-9_-]+", text.lower()))
    for part in re.findall(r"[\u4e00-\u9fff]+", text):
        output.update(part[index : index + 2] for index in range(len(part) - 1))
    return output


def search_cases(
    db: Session, actor: Actor, business: Business, query: str = "", valid_only: bool = False
) -> list[CaseRead]:
    """先限制可见范围，再按关键词排序，同分以更新时间和编号稳定排序。"""
    allow_business(actor, business)
    statement = select(Case).where(Case.business == business)
    if valid_only:
        statement = statement.where(Case.publication == "published", Case.validity == "verified")
    elif actor.role == "member":
        statement = statement.where((Case.publication == "published") | (Case.owner_id == actor.id))
    items = [
        CaseRead.model_validate(item)
        for item in db.scalars(statement.order_by(Case.updated_at.desc(), Case.id))
    ]
    if not query.strip():
        return items
    query_terms = terms(query)
    ranked: list[tuple[int, CaseRead]] = []
    for item in items:
        content = f"{item.title} {item.symptom} {item.conditions} {item.cause}"
        score = len(query_terms & terms(content)) + (10 if query.lower() in content.lower() else 0)
        if score:
            ranked.append((score, item))
    return [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)]


def preview_draft(db: Session, actor: Actor, business: Business, text: str) -> DraftPreview:
    """生成未持久化预览，远程等待后复核权限，模型不能决定验证或发布状态。"""
    allow_business(actor, business)
    content = DraftContent(title=" ".join(text.split())[:80], symptom=text)
    connection = active_connection(db)
    if connection:
        content = model_json(
            INTAKE_RULE, {"text": text, "business": business}, DraftContent, connection
        )
    actor = refresh_actor(db, actor)
    allow_business(actor, business)
    return DraftPreview(
        **content.model_dump(),
        rule_version=INTAKE_VERSION,
        mode="model" if connection else "local_rules",
        similar=search_cases(db, actor, business, text)[:3],
    )


def create_draft(
    db: Session, actor: Actor, source_id: str, content: DraftContent, key: str
) -> CaseRead:
    """先校验当前材料权限再执行幂等事务，权限撤销后也不能读取缓存草稿。"""
    actor = refresh_actor(db, actor)
    source = owned_source(db, actor, source_id)
    if source.owner_id != actor.id:
        raise BusinessError("FORBIDDEN", "只能使用自己提交的原始材料创建草稿", 403)
    return once(
        db,
        actor,
        key,
        "draft",
        {**json_object(content), "source_id": source_id},
        CaseRead,
        lambda: _save_draft(db, actor, source, content),
    )


def _save_draft(db: Session, actor: Actor, source: Source, content: DraftContent) -> CaseRead:
    item = Case(
        **content.model_dump(),
        source_id=source.id,
        business=source.business,
        owner_id=actor.id,
        rule_version=INTAKE_VERSION,
        publication="pending",
        validity="unverified",
    )
    db.add(item)
    db.flush()
    value = CaseRead.model_validate(item)
    db.add(
        CaseRevision(case_id=item.id, version=1, snapshot=json_object(value), editor_id=actor.id)
    )
    return value


def revise_case(
    db: Session, actor: Actor, case_id: str, version: int, changes: CaseChanges
) -> CaseRead:
    """校验人工确认规则，以预期版本更新并原子保存版本快照，冲突返回 409。"""
    result = apply_case_revision(db, actor, case_id, version, changes)
    db.commit()
    return result


def apply_case_revision(
    db: Session,
    actor: Actor,
    case_id: str,
    version: int,
    changes: CaseChanges,
    rule_version: str | None = None,
) -> CaseRead:
    """更新案例及历史快照但不提交，供反馈草稿发布在同一事务中复用确认规则。"""
    # 1. 检查可信身份、目标归属及状态转换的证据要求。
    item = owned_case(db, actor, case_id)
    validate_case_change(actor, item.owner_id, item.publication, changes)
    # 2. 写入条件带入版本与业务归属，不能覆盖其他编辑人的晚到更新。
    changed = db.execute(
        update(Case)
        .where(
            Case.id == case_id,
            Case.business.in_(actor.businesses),
            Case.version == version,
        )
        .values(
            **changes.model_dump(),
            **({"rule_version": rule_version} if rule_version else {}),
            version=version + 1,
            updated_at=timestamp(),
            verified_by=actor.id if changes.validity == "verified" else None,
        )
        .returning(Case.id),
        execution_options={"synchronize_session": False},
    )
    if changed.scalar_one_or_none() is None:
        db.rollback()
        raise BusinessError("VERSION_CONFLICT", "案例已被更新，请刷新后重新编辑", 409)
    # 3. 更新事实与新版本快照共同提交，旧版本继续保留以供追溯。
    db.refresh(item)
    result = CaseRead.model_validate(item)
    db.add(
        CaseRevision(
            case_id=item.id, version=item.version, snapshot=json_object(result), editor_id=actor.id
        )
    )
    return result


def revisions(db: Session, actor: Actor, case_id: str) -> list[RevisionRead]:
    """校验案例访问权后读取倒序快照，旧记录缺失的字段由兼容契约补足。"""
    owned_case(db, actor, case_id)
    return [
        RevisionRead.model_validate(item)
        for item in db.scalars(
            select(CaseRevision)
            .where(CaseRevision.case_id == case_id)
            .order_by(CaseRevision.version.desc())
        )
    ]
