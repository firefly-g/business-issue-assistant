"""在隔离旧库保留代表性案例，验证新增规则版本字段的无损升级。"""

from pathlib import Path

from alembic.config import Config
from pytest import MonkeyPatch
from sqlalchemy import MetaData, Table, create_engine, select

from alembic import command
from app.config import settings


def test_upgrade_preserves_existing_case(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """从首个迁移升级到当前版本，旧案例及关联关系保持原值。"""
    url = f"sqlite:///{tmp_path}/legacy.db"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config("alembic.ini")
    # 1. 构造真实旧表结构，使用反射而非当前 ORM 默认值插入历史数据。
    command.upgrade(config, "5c562a5fbf7f")
    engine = create_engine(url)
    with engine.begin() as connection:
        metadata = MetaData()
        users = Table("users", metadata, autoload_with=connection)
        sources = Table("sources", metadata, autoload_with=connection)
        cases = Table("cases", metadata, autoload_with=connection)
        connection.execute(
            users.insert(),
            {
                "id": "legacy-user",
                "email": "legacy@example.com",
                "name": "旧库测试",
                "role": "maintainer",
                "businesses": ["订单售后"],
                "password_hash": "test-only-digest",
            },
        )
        connection.execute(
            sources.insert(),
            {
                "id": "legacy-source",
                "business": "订单售后",
                "text": "历史原始依据",
                "owner_id": "legacy-user",
                "created_at": "2026-01-01T00:00:00+00:00",
                "version": 1,
            },
        )
        connection.execute(
            cases.insert(),
            {
                "id": "legacy-case",
                "title": "历史案例",
                "business": "订单售后",
                "symptom": "历史问题现象",
                "conditions": "历史适用条件",
                "investigation": "历史排查记录",
                "cause": "历史原因",
                "solution": "历史处理步骤",
                "verification": "历史验证事实",
                "publication": "published",
                "validity": "verified",
                "source_id": "legacy-source",
                "owner_id": "legacy-user",
                "version": 3,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-02T00:00:00+00:00",
                "is_demo": False,
            },
        )
    # 2. 执行真实升级后重新反射，检查新增默认及已有业务事实。
    command.upgrade(config, "head")
    with engine.connect() as connection:
        upgraded = Table("cases", MetaData(), autoload_with=connection)
        item = connection.execute(select(upgraded)).mappings().one()
        assert item["rule_version"] == "manual-v1"
        assert item["version"] == 3
        assert item["solution"] == "历史处理步骤"
        assert item["source_id"] == "legacy-source"
    engine.dispose()


def test_upgrade_preserves_enabled_model(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """已有模型转入列表，原密文及生效模式保持一致。"""
    url = f"sqlite:///{tmp_path}/model.db"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config("alembic.ini")
    command.upgrade(config, "17d95ea021a0")
    engine = create_engine(url)
    settings_data = {
        "id": 1,
        "version": 4,
        "mode": "model",
        "address": "https://provider.example/v1",
        "model": "existing-model",
        "encrypted_key": "opaque-fixture-ciphertext",
        "updated_by": "migration-fixture",
        "updated_at": "2026-11-18T00:00:00+00:00",
    }
    with engine.begin() as connection:
        original = Table("model_settings", MetaData(), autoload_with=connection)
        connection.execute(original.insert(), settings_data)
    command.upgrade(config, "head")
    with engine.connect() as connection:
        current = Table("model_settings", MetaData(), autoload_with=connection)
        profiles = Table("model_profiles", MetaData(), autoload_with=connection)
        active = connection.execute(select(current)).mappings().one()
        profile = connection.execute(select(profiles)).mappings().one()
        assert active == {**settings_data, "profile_id": profile["id"]}
        assert profile["model"] == settings_data["model"]
        assert profile["encrypted_key"] == settings_data["encrypted_key"]
    engine.dispose()
