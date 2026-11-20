"""提供团队模型配置、目录读取和试连接口，权限与事务交给用例层。"""

from fastapi import APIRouter

from ..application import model_settings
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
    ModelSettingsRead,
    ModelTestRead,
)
from .dependencies import DB, CurrentActor

router = APIRouter(prefix="/settings/model", tags=["模型配置"])


@router.get("", response_model=ModelSettingsRead, operation_id="readModelSettings")
def read(actor: CurrentActor, db: DB) -> ModelSettingsRead:
    """仅知识维护人可读取当前模式及凭证是否已配置。"""
    return model_settings.read_settings(db, actor)


@router.post("/models", response_model=ModelCatalogRead, operation_id="fetchModelCatalog")
def models(data: ModelCatalogInput, actor: CurrentActor, db: DB) -> ModelCatalogRead:
    """密钥通过请求体传递，读取该凭证可见的供应商模型。"""
    return model_settings.fetch_catalog(db, actor, data)


@router.post("/test", response_model=ModelTestRead, operation_id="testModelSettings")
def test(data: ModelConnectionInput, actor: CurrentActor, db: DB) -> ModelTestRead:
    """连接验证只发送合成内容，成功返回短期凭证。"""
    return model_settings.test_connection(db, actor, data)


@router.put("", response_model=ModelSettingsRead, operation_id="saveModelSettings")
def save(data: ModelSettingsInput, actor: CurrentActor, db: DB) -> ModelSettingsRead:
    """知识维护人保存通过验证的配置，成功后新请求立即使用。"""
    return model_settings.save_settings(db, actor, data)


@router.get("/profiles", response_model=ModelLibraryRead, operation_id="readModelLibrary")
def profiles(actor: CurrentActor, db: DB) -> ModelLibraryRead:
    """读取所有已保存模型，标记团队实际启用的一项。"""
    return model_settings.read_library(db, actor)


@router.post(
    "/profiles", response_model=ModelLibraryRead, status_code=201, operation_id="createModelProfile"
)
def create_profile(data: ModelProfileInput, actor: CurrentActor, db: DB) -> ModelLibraryRead:
    """将通过测试的配置加入列表，保留当前运行方式。"""
    return model_settings.save_profile(db, actor, data)


@router.put(
    "/profiles/{profile_id}", response_model=ModelLibraryRead, operation_id="updateModelProfile"
)
def update_profile(
    profile_id: str, data: ModelProfileInput, actor: CurrentActor, db: DB
) -> ModelLibraryRead:
    """保存选定配置的参数，若此项正在运行则同步更新其连接快照。"""
    return model_settings.save_profile(db, actor, data, profile_id)


@router.put("/active", response_model=ModelLibraryRead, operation_id="activateModelProfile")
def activate(data: ModelActivationInput, actor: CurrentActor, db: DB) -> ModelLibraryRead:
    """启用已保存的模型或切回本地规则，版本冲突时拒绝覆盖。"""
    return model_settings.activate_profile(db, actor, data)
