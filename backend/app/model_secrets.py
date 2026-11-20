"""使用独立密钥保护模型凭证和短期测试凭证，密钥与数据库分开保存。"""

import os
from tempfile import NamedTemporaryFile

from cryptography.fernet import Fernet

from .config import settings
from .domain.errors import BusinessError


def model_cipher(*, create: bool = False) -> Fernet:
    """使用部署密钥，开发环境首次配置时原子创建权限为 0600 的本地密钥。"""
    try:
        if settings.model_settings_key:
            return Fernet(settings.model_settings_key.encode("ascii"))
        if settings.app_env != "development":
            raise ValueError("部署密钥未配置")
        path = settings.model_settings_key_file
        if create and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            # 同时测试连接时只允许一个进程发布完整密钥，之后都读取同一文件。
            with NamedTemporaryFile(dir=path.parent) as temporary:
                temporary.write(Fernet.generate_key())
                temporary.flush()
                try:
                    os.link(temporary.name, path)
                except FileExistsError:
                    pass
        return Fernet(path.read_bytes())
    except (ValueError, OSError):
        raise BusinessError(
            "MODEL_SETTINGS_KEY_UNAVAILABLE", "模型配置加密密钥不可用，请检查服务端设置", 500
        ) from None
