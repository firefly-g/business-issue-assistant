"""定义业务输入值对象，约束文本与有限状态，权限和事务由用例负责。"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .types import Business, ChangeKind, Outcome, Publication, Validity


class Command(BaseModel):
    """统一文本清理规则，未知字段默认拒绝，口令字段单独保留空白。"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class DraftContent(Command):
    """案例事实字段，未知信息留空，文本内容不隐含已验证状态。"""

    title: str = Field(min_length=2, max_length=160, description="概括问题的案例标题")
    symptom: str = Field(min_length=2, max_length=10000, description="原始问题现象")
    conditions: str = Field(default="", max_length=10000, description="系统、渠道、版本及时间前提")
    investigation: str = Field(default="", max_length=10000, description="尝试操作及其观察结果")
    cause: str = Field(default="", max_length=10000, description="原因说明，未确认时留空")
    solution: str = Field(default="", max_length=10000, description="实际处理步骤及执行角色")
    verification: str = Field(
        default="", max_length=10000, description="验证人、验证条件及实际结果"
    )


class CaseChanges(DraftContent):
    """人工编辑目标值，发布状态与方案有效性分别校验。"""

    publication: Publication = Field(description="发布状态，与方案是否有效相互独立")
    validity: Validity = Field(description="方案有效性，已验证时必须保存验证依据")


class AnalysisCommand(Command):
    """分析问题的业务输入，关联材料仍须复核所属业务及所有者。"""

    text: str = Field(min_length=4, max_length=10000, description="问题及补充背景")
    business: Business = Field(description="本次分析所属业务")
    source_id: str | None = Field(default=None, description="本人提交的原始材料编号，可省略")


class Advice(Command):
    """模型可生成的建议字段，引用列表由服务端单独维护。"""

    summary: str = Field(min_length=1, max_length=5000, description="问题理解和证据不足说明")
    steps: list[Annotated[str, StringConstraints(min_length=1, max_length=2000)]] = Field(
        min_length=1, max_length=12, description="需要人工执行的排查步骤"
    )
    missing: list[Annotated[str, StringConstraints(min_length=1, max_length=1000)]] = Field(
        max_length=10, description="仍需补充的信息"
    )
    reply: str = Field(min_length=1, max_length=5000, description="供人工复制的回复草稿")


class FeedbackCommand(Command):
    """本次实际处理结果，单次失败不自动使历史案例失效。"""

    outcome: Outcome = Field(description="本次问题的处理结果")
    note: str = Field(min_length=2, max_length=5000, description="实际操作、观察结果和确认情况")


class FeedbackDraftChanges(Command):
    """完整保存案例提案；修订必须明确目标及人工核对过的基础版本。"""

    content: DraftContent = Field(description="人工校正后的案例事实")
    kind: ChangeKind = Field(description="新增案例或修订已有案例")
    target_case_id: str | None = Field(default=None, min_length=1, max_length=36)
    target_version: int | None = Field(default=None, ge=1, description="人工核对的目标案例版本")
    status: Literal["draft", "pending"] = Field(description="保存编辑或提交人工确认")

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        """新增不得夹带修订目标，修订不得缺少版本，避免隐式覆盖正式案例。"""
        if self.kind == "revise":
            if self.target_case_id is None or self.target_version is None:
                raise ValueError("修订草稿必须选择目标案例及其版本")
        elif self.target_case_id is not None or self.target_version is not None:
            raise ValueError("新增草稿不能包含修订目标")
        return self
