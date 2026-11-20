"""读写团队模型设置，先授权再测试，版本和测试凭证共同约束配置发布。"""

import hashlib
import hmac
import json

from cryptography.fernet import InvalidToken
from pydantic import BaseModel, StrictBool
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..contracts.inputs import (
    ModelActivationInput,
    ModelCatalogInput,
    ModelConnectionInput,
    ModelProfileInput,
    ModelSettingsInput,
)
from ..contracts.responses import (
    ModelCatalogRead,
    ModelLibraryRead,
    ModelProfileRead,
    ModelSettingsRead,
    ModelTestRead,
)
from ..domain.errors import BusinessError
from ..domain.policies import require_role
from ..domain.types import Actor, AnalysisMode
from ..model_connection import ModelConnection, managed_endpoint
from ..model_secrets import model_cipher
from ..models import ModelProfile, ModelSettings, identifier, timestamp
from ..provider import list_model_ids, model_json
from .identity import refresh_actor

_ENVIRONMENT_ID = "environment"


def _is_environment(row: ModelSettings | None) -> bool:
    # 环境变量配置作为独立的列表项，生效时引用部署原值，不复制其密钥。
    return row is None or (row.mode == "model" and not row.profile_id and not row.encrypted_key)


def _project(row: ModelSettings | None) -> ModelSettingsRead:
    if _is_environment(row):
        return ModelSettingsRead(
            mode="model" if settings.model_enabled else "local_rules",
            address=settings.model_base_url,
            model=settings.model_name,
            has_api_key=bool(settings.model_api_key),
            version=row.version if row else 0,
        )
    assert row is not None
    return ModelSettingsRead(
        mode=row.mode,
        address=row.address,
        model=row.model,
        has_api_key=bool(row.encrypted_key),
        version=row.version,
    )


def runtime_mode(db: Session) -> AnalysisMode:
    """读取真正生效的运行模式，不解密密钥。"""
    return _project(db.get(ModelSettings, 1)).mode


def _decrypt(encrypted: str) -> str:
    try:
        return model_cipher().decrypt(encrypted.encode()).decode()
    except (InvalidToken, UnicodeError):
        raise BusinessError(
            "MODEL_KEY_UNAVAILABLE", "已存密钥无法读取，请重新填写密钥", 500
        ) from None


def _key(row: ModelSettings | None) -> str:
    if row is None or _is_environment(row):
        return settings.model_api_key
    return _decrypt(row.encrypted_key)


def active_connection(db: Session) -> ModelConnection | None:
    """每个用例读取一次连接快照，后续配置变更不会改变请求对应的模型名称。"""
    row = db.get(ModelSettings, 1)
    value = _project(row)
    if value.mode == "local_rules":
        return None
    return ModelConnection(value.address, value.model, _key(row), managed=not _is_environment(row))


def read_settings(db: Session, actor: Actor) -> ModelSettingsRead:
    """仅知识维护人可读取连接元信息，响应永远不回传密钥。"""
    require_role(actor, "maintainer")
    return _project(db.get(ModelSettings, 1))


def _credentials(
    db: Session, data: ModelCatalogInput, row: ModelSettings | None
) -> tuple[str, str]:
    current = _project(row)
    if current.version != data.version:
        raise _conflict()
    address = str(managed_endpoint(data.address)).rstrip("/")
    key = data.api_key.get_secret_value().strip() if data.api_key else ""
    # 地址改变时必须主动提交密钥，避免将已有凭证转发给其他服务。
    if not key:
        if data.credential_profile_id == _ENVIRONMENT_ID:
            if settings.model_enabled and address == settings.model_base_url.rstrip("/"):
                key = settings.model_api_key
        elif data.credential_profile_id:
            profile = _find_profile(db, data.credential_profile_id)
            if address == profile.address.rstrip("/"):
                key = _decrypt(profile.encrypted_key)
        elif current.has_api_key and address == current.address.rstrip("/"):
            key = _key(row)
    if not key:
        raise BusinessError("MODEL_FIELDS_REQUIRED", "请填写 API 密钥", 422)
    if not key.isascii() or any(char.isspace() or not char.isprintable() for char in key):
        raise BusinessError("MODEL_KEY_INVALID", "API 密钥中包含不支持的字符", 422)
    return address, key


def _candidate(
    db: Session, data: ModelConnectionInput, row: ModelSettings | None
) -> ModelConnection:
    address, key = _credentials(db, data, row)
    if not data.model:
        raise BusinessError("MODEL_FIELDS_REQUIRED", "请选择模型", 422)
    return ModelConnection(address, data.model, key)


def fetch_catalog(db: Session, actor: Actor, data: ModelCatalogInput) -> ModelCatalogRead:
    """使用待配置的供应商凭证列出模型，只读远端目录，不改变团队配置。"""
    require_role(actor, "maintainer")
    address, key = _credentials(db, data, db.get(ModelSettings, 1))
    models = list_model_ids(address, key)
    require_role(refresh_actor(db, actor), "maintainer")
    return ModelCatalogRead(models=models)


def _proof(actor: Actor, version: int, connection: ModelConnection) -> bytes:
    payload = json.dumps(
        [actor.id, version, connection.address, connection.model, connection.api_key]
    )
    return b"model-test:" + hashlib.sha256(payload.encode()).digest()


class _Probe(BaseModel):
    ok: StrictBool


def test_connection(db: Session, actor: Actor, data: ModelConnectionInput) -> ModelTestRead:
    """仅发送固定测试内容，无业务资料。通过后签发有效期十分钟的配置凭证。"""
    require_role(actor, "maintainer")
    connection = _candidate(db, data, db.get(ModelSettings, 1))
    cipher = model_cipher(create=True)
    response = model_json('返回 JSON 对象 {"ok": true}，用于连接测试。', {}, _Probe, connection)
    if not response.ok:
        raise BusinessError("MODEL_TEST_FAILED", "模型返回格式与连接测试要求不符", 502)
    require_role(refresh_actor(db, actor), "maintainer")
    return ModelTestRead(
        test_token=cipher.encrypt(_proof(actor, data.version, connection)).decode()
    )


def _conflict() -> BusinessError:
    return BusinessError("MODEL_SETTINGS_CONFLICT", "配置已被其他维护人更新，请重新加载", 409)


def _verified_key(actor: Actor, version: int, connection: ModelConnection, token: str) -> str:
    if not token:
        raise BusinessError("MODEL_TEST_REQUIRED", "请先测试当前连接后再保存", 422)
    cipher = model_cipher()
    try:
        valid = hmac.compare_digest(
            cipher.decrypt(token.encode(), ttl=600), _proof(actor, version, connection)
        )
    except InvalidToken:
        valid = False
    if not valid:
        raise BusinessError("MODEL_TEST_REQUIRED", "请重新测试当前连接后再保存", 422)
    return cipher.encrypt(connection.api_key.encode()).decode()


def save_settings(db: Session, actor: Actor, data: ModelSettingsInput) -> ModelSettingsRead:
    """兼容旧版一次保存并启用的接口，新连接同时写入配置列表。"""
    require_role(actor, "maintainer")
    row = db.get(ModelSettings, 1)
    current = _project(row)
    if data.version != current.version:
        raise _conflict()
    if data.mode == "model":
        connection = _candidate(db, data, row)
        token = data.test_token.get_secret_value() if data.test_token else ""
        encrypted = _verified_key(actor, data.version, connection, token)
        profile = ModelProfile(
            id=identifier(),
            address=connection.address,
            model=connection.model,
            encrypted_key=encrypted,
        )
        db.add(profile)
        db.flush()
        _write_runtime(db, actor, row, data.version, "model", profile)
    else:
        _write_runtime(db, actor, row, data.version, "local_rules")
    return _project(db.get(ModelSettings, 1, populate_existing=True))


def _find_profile(db: Session, profile_id: str) -> ModelProfile:
    profile = db.get(ModelProfile, profile_id)
    if not profile:
        raise BusinessError("NOT_FOUND", "模型配置不存在，请重新加载", 404)
    return profile


def _write_runtime(
    db: Session,
    actor: Actor,
    row: ModelSettings | None,
    version: int,
    mode: AnalysisMode,
    profile: ModelProfile | None = None,
    *,
    environment: bool = False,
) -> None:
    # 同一个版本串行化列表修改和启用切换，防止旧请求覆盖已启用的模型。
    address, model, encrypted, profile_id = "", "", "", None
    if profile is not None:
        address, model, encrypted, profile_id = (
            profile.address,
            profile.model,
            profile.encrypted_key,
            profile.id,
        )
    elif row is not None and not environment:
        address, model, encrypted, profile_id = (
            row.address,
            row.model,
            row.encrypted_key,
            row.profile_id,
        )
    elif row is None and mode == "local_rules" and settings.model_enabled:
        address, model = settings.model_base_url, settings.model_name
        encrypted = model_cipher(create=True).encrypt(settings.model_api_key.encode()).decode()
    values = {
        "version": version + 1,
        "mode": mode,
        "address": address,
        "model": model,
        "encrypted_key": encrypted,
        "updated_by": actor.id,
        "updated_at": timestamp(),
        "profile_id": profile_id,
    }
    if row is None:
        db.add(ModelSettings(id=1, **values))
    else:
        updated = db.scalar(
            update(ModelSettings)
            .where(ModelSettings.id == 1, ModelSettings.version == version)
            .values(**values)
            .returning(ModelSettings.id)
        )
        if updated is None:
            raise _conflict()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _conflict() from None


def read_library(db: Session, actor: Actor) -> ModelLibraryRead:
    """列出团队备用配置，当前运行方式独立于列表顺序。"""
    require_role(actor, "maintainer")
    row = db.get(ModelSettings, 1)
    current = _project(row)
    profiles = [
        ModelProfileRead(
            id=item.id, address=item.address, model=item.model, has_api_key=bool(item.encrypted_key)
        )
        for item in db.scalars(select(ModelProfile).order_by(ModelProfile.model, ModelProfile.id))
    ]
    if settings.model_enabled:
        profiles.insert(
            0,
            ModelProfileRead(
                id=_ENVIRONMENT_ID,
                address=settings.model_base_url,
                model=settings.model_name,
                has_api_key=True,
            ),
        )
    active_id = None
    if current.mode == "model":
        active_id = _ENVIRONMENT_ID if _is_environment(row) else row.profile_id if row else None
    return ModelLibraryRead(
        mode=current.mode, active_profile_id=active_id, version=current.version, profiles=profiles
    )


def save_profile(
    db: Session, actor: Actor, data: ModelProfileInput, profile_id: str | None = None
) -> ModelLibraryRead:
    """保存一套验证过的配置，新增不启用，编辑已启用项时同步更新其运行快照。"""
    require_role(actor, "maintainer")
    row = db.get(ModelSettings, 1)
    connection = _candidate(db, data, row)
    encrypted = _verified_key(actor, data.version, connection, data.test_token.get_secret_value())
    if profile_id is None:
        profile = ModelProfile(id=identifier())
        db.add(profile)
    else:
        profile = _find_profile(db, profile_id)
    profile.address, profile.model, profile.encrypted_key = (
        connection.address,
        connection.model,
        encrypted,
    )
    db.flush()
    # 只在该项已是运行快照的来源时同步值，备用项保持独立。
    current = _project(row)
    tracked = profile if row and row.profile_id == profile.id else None
    _write_runtime(db, actor, row, data.version, current.mode, tracked)
    return read_library(db, actor)


def activate_profile(db: Session, actor: Actor, data: ModelActivationInput) -> ModelLibraryRead:
    """切换单一生效项，确认密钥可读后提交，其他已保存模型继续保留。"""
    require_role(actor, "maintainer")
    row = db.get(ModelSettings, 1)
    if _project(row).version != data.version:
        raise _conflict()
    environment = data.profile_id == _ENVIRONMENT_ID
    profile = None
    if environment and not settings.model_enabled:
        raise BusinessError("NOT_FOUND", "环境变量模型已不可用", 404)
    if data.profile_id and not environment:
        profile = _find_profile(db, data.profile_id)
        _decrypt(profile.encrypted_key)
    _write_runtime(
        db,
        actor,
        row,
        data.version,
        "model" if data.profile_id else "local_rules",
        profile,
        environment=environment,
    )
    return read_library(db, actor)
