"""定义有限业务状态和可信身份，作为授权与状态转换的公共契约。"""

from dataclasses import dataclass
from typing import Literal

Business = Literal["订单售后", "营销活动", "系统支持"]
Role = Literal["member", "handler", "maintainer"]
Publication = Literal["draft", "pending", "published", "archived"]
Validity = Literal["unverified", "verified", "invalid"]
Progress = Literal["processing", "resolved", "reopened"]
Outcome = Literal["resolved", "unresolved", "not_applicable"]
AnalysisMode = Literal["model", "local_rules"]
# 变更草稿独立于正式案例；修订提案只有发布后才更新目标案例。
ChangeKind = Literal["create", "revise"]
ChangeStatus = Literal["draft", "pending", "published"]
BUSINESSES: tuple[Business, ...] = ("订单售后", "营销活动", "系统支持")


@dataclass(frozen=True)
class Actor:
    """服务端已验证的账号快照，业务范围只从存储中的身份恢复。"""

    id: str
    email: str
    name: str
    role: Role
    businesses: tuple[Business, ...]
