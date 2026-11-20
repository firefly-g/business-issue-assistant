"""在启动边界集中读取并校验配置，错误与对象表示均隐藏秘密字段。"""

from pathlib import Path
from typing import Self
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """运行配置，模型服务参数需同时提供，文件系统写入由实际业务入口执行。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    database_url: str = Field(default="sqlite:///./data/assistant.db", repr=False)
    upload_dir: Path = Path("data/uploads")
    admin_email: str = Field(default="admin@example.com", min_length=3, max_length=255)
    admin_name: str = Field(default="知识维护人", min_length=1, max_length=80)
    admin_password: str = Field(default="local-dev-2026", min_length=10, max_length=256, repr=False)
    cookie_secure: bool = False
    app_env: str = "development"
    model_base_url: str = ""
    model_api_key: str = Field(default="", repr=False)
    model_name: str = ""
    model_settings_key: str = Field(default="", repr=False)
    model_settings_key_file: Path = Path("data/model-settings.key")

    @property
    def model_enabled(self) -> bool:
        """三项参数齐备才启用模型，部分配置在启动校验时拒绝。"""
        return bool(self.model_base_url and self.model_api_key and self.model_name)

    @model_validator(mode="after")
    def validate_runtime(self) -> Self:
        """拒绝不完整模型配置及部署环境的演示口令，异常不回显具体秘密。"""
        if self.app_env != "development" and self.admin_password == "local-dev-2026":
            raise ValueError("部署环境必须设置 ADMIN_PASSWORD")
        if (
            any((self.model_base_url, self.model_api_key, self.model_name))
            and not self.model_enabled
        ):
            raise ValueError("模型服务需要同时配置 MODEL_BASE_URL、MODEL_API_KEY、MODEL_NAME")
        if self.model_enabled:
            endpoint = urlparse(self.model_base_url)
            if endpoint.scheme not in ("http", "https") or not endpoint.netloc:
                raise ValueError("MODEL_BASE_URL 必须是有效的 HTTP 服务地址")
        return self


settings = Settings()
