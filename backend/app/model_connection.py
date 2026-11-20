"""提供模型连接快照，并限制网页配置发起的服务端网络访问。"""

from dataclasses import dataclass, field
from ipaddress import IPv6Address, ip_address
from socket import SOCK_STREAM, getaddrinfo

import httpx

from .domain.errors import BusinessError


@dataclass(frozen=True)
class ModelConnection:
    """一次调用使用的连接快照，网页地址需要在每次连接时复核。"""

    address: str
    model: str
    api_key: str = field(repr=False)
    managed: bool = True


def managed_endpoint(address: str) -> httpx.URL:
    """只接受标准端口的 HTTPS 基础地址，拒绝内联凭证、查询参数和片段。"""
    try:
        url = httpx.URL(address.strip())
    except httpx.InvalidURL:
        raise BusinessError(
            "MODEL_ADDRESS_INVALID", "请输入有效的 HTTPS 模型接口地址", 422
        ) from None
    if (
        url.scheme != "https"
        or not url.host
        or url.port not in (None, 443)
        or url.userinfo
        or url.query
        or url.fragment
        or url.path.rstrip("/").endswith("/chat/completions")
    ):
        raise BusinessError(
            "MODEL_ADDRESS_INVALID", "请填写 HTTPS 基础地址，使用标准端口并去掉接口后缀", 422
        )
    return url


def public_address(host: str) -> str:
    """拒绝非公网解析结果，并返回本次连接必须使用的已验证地址。"""
    try:
        addresses = [ip_address(entry[4][0]) for entry in getaddrinfo(host, 443, type=SOCK_STREAM)]
    except OSError:
        raise BusinessError(
            "MODEL_DNS_FAILED", "无法解析模型服务域名，请检查接口地址", 502
        ) from None
    if not addresses or any(
        not addr.is_global
        or addr.is_multicast
        or addr.is_reserved
        or (isinstance(addr, IPv6Address) and addr.is_site_local)
        for addr in addresses
    ):
        raise BusinessError("MODEL_ADDRESS_INVALID", "网页配置仅支持公网模型服务地址", 422)
    # 本机可能没有 IPv6 出口，有 IPv4 时优先使用。
    return str(min(addresses, key=lambda addr: addr.version))
