"""编排授权检索、模型建议与运行快照，远端调用完成后才开始业务写入。"""

from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..contracts.responses import (
    AnalysisRead,
    AnalysisResult,
    CitationRead,
    FeedbackRead,
    QuestionRead,
    RunRead,
    json_object,
)
from ..domain.commands import Advice, AnalysisCommand, FeedbackCommand
from ..domain.errors import BusinessError
from ..domain.policies import allow_business
from ..domain.types import Actor
from ..models import AnalysisRun, Case, Feedback, Question, Source
from ..provider import model_json
from .cases import search_cases
from .identity import refresh_actor
from .materials import owned_source
from .model_settings import active_connection
from .rules import ANALYSIS_RULE, RULE_VERSION


def _local_result(citations: list[CitationRead]) -> AnalysisResult:
    return AnalysisResult(
        summary="已按问题描述检索团队已验证案例。"
        if citations
        else "暂未找到适用的已验证案例，请补充背景后继续排查。",
        steps=[
            "确认涉及的系统、业务渠道、版本及问题发生时间。",
            "记录已尝试的操作及实际结果，保留原始报错或截图。",
        ]
        + (
            ["逐条比较下方案例的适用条件，再由有权限的处理人核对。"]
            if citations
            else ["将问题交由对应处理人跟进，解决后补充可复用的经验。"]
        ),
        missing=["具体业务编号和发生时间", "所用系统、渠道与版本", "已尝试的处理操作及结果"],
        citations=citations,
        mode="local_rules",
        reply="已记录此问题。请补充业务编号、发生时间、系统或渠道及已尝试的操作，我们会结合团队历史经验进一步核对。",
        notice="本地规则分析 · 根据关键词检索，历史案例需核对适用条件。",
    )


def analyze(db: Session, actor: Actor, command: AnalysisCommand) -> AnalysisRead:
    """读取有效证据并生成建议，提问、运行和幂等记录由调用方共同提交。"""
    # 1. 核对输入材料归属，并批量读取候选来源版本，避免逐条查询附件元数据。
    start = perf_counter()
    allow_business(actor, command.business)
    source_text = ""
    if command.source_id:
        source = owned_source(db, actor, command.source_id)
        if source.business != command.business:
            raise BusinessError("INVALID_INPUT", "材料与问题必须属于同一业务", 422)
        if source.owner_id != actor.id:
            raise BusinessError("FORBIDDEN", "只能将自己的材料附加到问题", 403)
        source_text = source.text
    candidates = search_cases(db, actor, command.business, command.text, valid_only=True)[:5]
    versions = {
        source_id: version
        for source_id, version in db.execute(
            select(Source.id, Source.version).where(
                Source.id.in_([item.source_id for item in candidates])
            )
        )
    }
    citations = [
        CitationRead(**item.model_dump(), source_version=versions[item.source_id])
        for item in candidates
    ]
    # 2. 模型只能返回建议字段，引用由授权检索确定，失败不写入成功记录。
    result = _local_result(citations)
    connection = active_connection(db)
    if connection:
        advice = model_json(
            ANALYSIS_RULE,
            {
                "question": command.text,
                "business": command.business,
                "cases": [json_object(item) for item in citations],
                "source_text": source_text,
            },
            Advice,
            connection,
        )
        result = AnalysisResult(
            **advice.model_dump(),
            citations=citations,
            mode="model",
            notice="模型辅助分析 · 请核对历史案例的适用条件及原始依据。",
        )
    # 3. 网络等待后重读权限，撤销业务权限时不保存结果或幂等成功记录。
    actor = refresh_actor(db, actor)
    allow_business(actor, command.business)
    # 4. 外部调用结束后再写入业务事实，避免长时间持有数据库写锁。
    question = Question(
        text=command.text, business=command.business, source_id=command.source_id, owner_id=actor.id
    )
    db.add(question)
    db.flush()
    run = AnalysisRun(
        question_id=question.id,
        rule_version=RULE_VERSION,
        model=connection.model if connection else "local-rules-v1",
        result=json_object(result),
        duration_ms=int((perf_counter() - start) * 1000),
    )
    db.add(run)
    db.flush()
    return AnalysisRead(
        question=QuestionRead.model_validate(question), run=RunRead.model_validate(run)
    )


def present_analysis(db: Session, actor: Actor, value: AnalysisRead) -> AnalysisRead:
    """重新核对历史引用的权限和当前版本，旧建议不继续当作当前有效方案展示。"""
    actor = refresh_actor(db, actor)
    allow_business(actor, value.question.business)
    originals = value.run.result.citations
    visible = select(Case).where(
        Case.id.in_([item.id for item in originals]), Case.business.in_(actor.businesses)
    )
    if actor.role == "member":
        visible = visible.where((Case.publication == "published") | (Case.owner_id == actor.id))
    # 身份映射可能缓存写入前的案例，显式刷新才能发现其他事务刚完成的失效操作。
    current = {
        item.id: item for item in db.scalars(visible.execution_options(populate_existing=True))
    }
    citations: list[CitationRead] = []
    changed = False
    for snapshot in originals:
        item = current.get(snapshot.id)
        if not item:
            changed = True
            continue
        available = (
            item.publication == "published"
            and item.validity == "verified"
            and item.version == snapshot.version
        )
        changed = changed or not available
        citations.append(snapshot.model_copy(update={"currently_available": available}))
    result = value.run.result.model_copy(update={"citations": citations})
    if changed:
        # 引用变化时同步撤回依赖旧证据的文字，保留快照仅供追溯。
        result = result.model_copy(
            update={
                "summary": "引用案例已发生变化，请重新分析当前问题。",
                "steps": [
                    "核对当前问题的系统、渠道、时间和已尝试操作。",
                    "重新提交分析，获取当前有效的案例。",
                ],
                "reply": "此问题的历史参考资料已更新，需要重新核对后给出处理建议。",
                "notice": "历史分析 · 引用版本已变化，原建议需重新核对。",
            }
        )
    return value.model_copy(update={"run": value.run.model_copy(update={"result": result})})


def my_question(db: Session, actor: Actor, question_id: str) -> Question:
    """限制个人记录归属，不向其他账号暴露提问是否存在。"""
    item = db.scalar(
        select(Question).where(
            Question.id == question_id,
            Question.owner_id == actor.id,
            Question.business.in_(actor.businesses),
        )
    )
    if not item:
        raise BusinessError("NOT_FOUND", "提问记录不存在", 404)
    return item


def question_detail(db: Session, actor: Actor, question_id: str) -> AnalysisRead:
    """读取本人提问、运行与实际反馈，历史引用在响应前重新验证。"""
    question = my_question(db, actor, question_id)
    run = db.scalar(select(AnalysisRun).where(AnalysisRun.question_id == question_id))
    if not run:
        raise BusinessError("DATA_INTEGRITY_ERROR", "分析记录不完整，请联系维护人", 500)
    value = AnalysisRead(
        question=QuestionRead.model_validate(question),
        run=RunRead.model_validate(run),
        feedback=[
            FeedbackRead.model_validate(item)
            for item in db.scalars(
                select(Feedback)
                .where(Feedback.question_id == question_id)
                .order_by(Feedback.created_at, Feedback.id)
            )
        ],
    )
    return present_analysis(db, actor, value)


def save_feedback(
    db: Session, actor: Actor, question_id: str, command: FeedbackCommand
) -> FeedbackRead:
    """追加实际反馈并更新提问进度，提交由上层幂等事务统一完成。"""
    question = my_question(db, actor, question_id)
    item = Feedback(
        question_id=question.id, author_id=actor.id, outcome=command.outcome, note=command.note
    )
    question.progress = "resolved" if command.outcome == "resolved" else "reopened"
    db.add(item)
    db.flush()
    return FeedbackRead.model_validate(item)
