"""在测试收集前隔离数据库和文件目录，避免任何测试导入读写本机演示库。"""

import os
import tempfile
from collections.abc import Generator

import pytest

_test_dir = tempfile.TemporaryDirectory(prefix="business-standards-test-")
os.environ["DATABASE_URL"] = (
    os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_test_dir.name}/test.db"
)
os.environ["UPLOAD_DIR"] = f"{_test_dir.name}/uploads"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["APP_ENV"] = "development"
os.environ["COOKIE_SECURE"] = "false"
os.environ["ADMIN_PASSWORD"] = "test-only-password-2026"
os.environ["MODEL_BASE_URL"] = ""
os.environ["MODEL_API_KEY"] = ""
os.environ["MODEL_NAME"] = ""
os.environ["MODEL_SETTINGS_KEY"] = ""
os.environ["MODEL_SETTINGS_KEY_FILE"] = f"{_test_dir.name}/model-settings.key"


@pytest.fixture(scope="session", autouse=True)
def isolated_storage() -> Generator[None, None, None]:
    """所有用例结束后释放连接再清理合成材料，测试数据库不进入仓库。"""
    from alembic.config import Config

    from alembic import command

    command.upgrade(Config("alembic.ini"), "head")
    yield
    from app.db import engine

    engine.dispose()
    _test_dir.cleanup()
