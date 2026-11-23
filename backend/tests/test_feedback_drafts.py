"""以隔离合成数据验证反馈转案例的新增、修订、权限、模型恢复及原子发布。"""

import os
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import JsonValue
from sqlalchemy import func, select, update

from app.application import analysis, feedback_generation
from app.db import SessionLocal
from app.domain.commands import DraftContent
from app.domain.errors import BusinessError
from app.main import app
from app.model_connection import ModelConnection
from app.models import FeedbackDraft, User


@pytest.fixture
def admin(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """每项用例固定为本地模式，模型分支单独替换，不依赖其他测试保存的配置。"""
    monkeypatch.setattr(analysis, "active_connection", lambda db: None)
    monkeypatch.setattr(feedback_generation, "active_connection", lambda db: None)
    with TestClient(app) as browser:
        response = browser.post(
            "/api/auth/login",
            json={
                "email": "admin@example.com",
                "password": os.environ["ADMIN_PASSWORD"],
            },
        )
        assert response.status_code == 200
        yield browser


def key() -> dict[str, str]:
    """为不同逻辑请求生成键，重试场景显式复用。"""
    return {"Idempotency-Key": str(uuid4())}


def person(admin: TestClient, business: str = "订单售后") -> tuple[TestClient, str]:
    """创建单业务普通成员，调用方负责关闭客户端。"""
    email = f"feedback-{uuid4()}@example.com"
    payload = {
        "email": email,
        "password": "test-only-password",
        "name": "反馈测试成员",
        "businesses": [business],
    }
    result = admin.post("/api/users", json=payload)
    assert result.status_code == 201
    browser = TestClient(app)
    assert (
        browser.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": payload["password"],
            },
        ).status_code
        == 200
    )
    return browser, result.json()["id"]


def feedback(
    browser: TestClient,
    business: str = "订单售后",
    source_id: str | None = None,
    outcome: str = "resolved",
) -> tuple[str, str]:
    """通过公开接口产生独立问题和实际反馈，避免直接构造不可能的业务状态。"""
    response = browser.post(
        "/api/analyses",
        json={
            "text": "合成回流样本核对订单处理状态",
            "business": business,
            "source_id": source_id,
        },
        headers=key(),
    )
    assert response.status_code == 201, response.text
    question_id = response.json()["question"]["id"]
    result = browser.post(
        f"/api/questions/{question_id}/feedback",
        json={
            "outcome": outcome,
            "note": "处理人按渠道甲核对流水并恢复状态，客服确认结果",
        },
        headers=key(),
    )
    assert result.status_code == 201
    return question_id, result.json()["id"]


def generate(browser: TestClient, ids: tuple[str, str]) -> dict[str, JsonValue]:
    """首次整理生成草稿，同份反馈重新打开仍应返回原编号。"""
    response = browser.post(f"/api/questions/{ids[0]}/feedback/{ids[1]}/draft", headers=key())
    assert response.status_code == 201, response.text
    return response.json()


def submit(
    browser: TestClient, draft: dict[str, JsonValue], **changes: object
) -> dict[str, JsonValue]:
    """人工补齐有效性所需字段后提交，不能借此直接发布。"""
    content = {
        **draft["content"],
        "conditions": "仅渠道甲",
        "solution": "核对流水后按流程恢复",
        "verification": "客服核对订单恢复，本次操作已确认",
    }
    payload = {
        "version": draft["version"],
        "content": content,
        "kind": draft["kind"],
        "target_case_id": draft["target_case_id"],
        "target_version": draft["target_version"],
        "status": "pending",
        **changes,
    }
    response = browser.put(f"/api/feedback-drafts/{draft['id']}", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def publish(
    browser: TestClient,
    draft: dict[str, JsonValue],
    validity: str = "verified",
    headers: dict[str, str] | None = None,
) -> dict[str, JsonValue]:
    """维护人显式选择方案状态，返回草稿记录的发布去向。"""
    response = browser.post(
        f"/api/feedback-drafts/{draft['id']}/publish",
        json={
            "version": draft["version"],
            "validity": validity,
        },
        headers=headers or key(),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_new_case_replay_and_published_evidence(admin: TestClient) -> None:
    """普通成员整理与提交，维护人发布后其他成员才能读取原始截图和反馈依据。"""
    owner, _ = person(admin)
    reader, _ = person(admin)
    try:
        image = b"\x89PNG\r\n\x1a\nsynthetic-test-image"
        source = owner.post(
            "/api/sources",
            data={"business": "订单售后", "text": "截图背景原文"},
            files={"file": ("sample.png", image, "image/png")},
        ).json()
        ids = feedback(owner, source_id=source["id"])
        pending_before = admin.get("/api/overview").json()["pending"]
        draft = generate(owner, ids)
        assert draft["status"] == "draft"
        assert draft["content"]["solution"] == ""
        assert draft["content"]["verification"] == ""
        assert reader.get(f"/api/sources/{source['id']}/attachment").status_code == 404
        pending = submit(owner, draft)
        assert admin.get("/api/overview").json()["pending"] == pending_before + 1
        assert reader.get("/api/overview").json()["pending"] == 0
        reopened = generate(owner, ids)
        assert reopened["id"] == draft["id"]
        assert reopened["version"] == pending["version"]
        assert reopened["generated_content"] == draft["content"]
        assert len(reopened["history"]) == 2
        assert (
            owner.post(
                f"/api/feedback-drafts/{draft['id']}/publish",
                json={
                    "version": pending["version"],
                    "validity": "verified",
                },
                headers=key(),
            ).status_code
            == 403
        )
        publish_key = key()
        published = publish(admin, pending, headers=publish_key)
        assert admin.get("/api/overview").json()["pending"] == pending_before
        replay = publish(admin, pending, headers=publish_key)
        assert replay["published_case_id"] == published["published_case_id"]
        case_id = published["published_case_id"]
        case = reader.get(f"/api/cases/{case_id}").json()
        assert case["publication"] == "published" and case["validity"] == "verified"
        assert reader.get(f"/api/sources/{source['id']}/attachment").status_code == 200
        evidence = reader.get(f"/api/cases/{case_id}/feedback-evidence").json()
        assert evidence[0]["note"] == draft["evidence"]["feedback"]["note"]
        assert "run" not in evidence[0] and "history" not in evidence[0]
        assert reader.get(f"/api/feedback-drafts/{draft['id']}").status_code == 404
        result = reader.post(
            "/api/analyses",
            json={
                "text": case["symptom"],
                "business": "订单售后",
            },
            headers=key(),
        ).json()
        assert case_id in [item["id"] for item in result["run"]["result"]["citations"]]
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(FeedbackDraft)
                    .where(FeedbackDraft.feedback_id == ids[1])
                )
                == 1
            )
    finally:
        owner.close()
        reader.close()


def test_revision_conflict_is_atomic_and_can_be_rebased(admin: TestClient) -> None:
    """修订前正式案例不变，目标晚到更新时草稿发布回滚，人工核对新版本后才能发布。"""
    original = publish(admin, submit(admin, generate(admin, feedback(admin))))
    case_id = original["published_case_id"]
    case = admin.get(f"/api/cases/{case_id}").json()
    draft = generate(admin, feedback(admin))
    pending = submit(
        admin, draft, kind="revise", target_case_id=case_id, target_version=case["version"]
    )
    assert admin.get(f"/api/cases/{case_id}").json()["version"] == case["version"]
    fields = (
        "title",
        "symptom",
        "conditions",
        "investigation",
        "cause",
        "solution",
        "verification",
        "publication",
        "validity",
        "version",
    )
    updated = admin.put(
        f"/api/cases/{case_id}",
        json={
            **{field: case[field] for field in fields},
            "conditions": "新增渠道限制",
        },
    )
    assert updated.status_code == 200
    conflict = admin.post(
        f"/api/feedback-drafts/{draft['id']}/publish",
        json={
            "version": pending["version"],
            "validity": "verified",
        },
        headers=key(),
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "TARGET_VERSION_CONFLICT"
    current = admin.get(f"/api/feedback-drafts/{draft['id']}").json()
    assert current["status"] == "pending" and current["version"] == pending["version"]
    assert len(current["history"]) == len(pending["history"])
    rebased = submit(admin, current, target_version=2)
    published = publish(admin, rebased)
    assert published["published_case_id"] == case_id
    assert published["published_case_version"] == 3
    revisions = admin.get(f"/api/cases/{case_id}/revisions").json()
    assert [item["version"] for item in revisions] == [3, 2, 1]
    assert len(admin.get(f"/api/cases/{case_id}/feedback-evidence").json()) == 2


def test_authorization_target_validation_and_draft_conflict(admin: TestClient) -> None:
    """草稿、目标及输入均验证权限，旧草稿版本不能覆盖他人修正。"""
    owner, owner_id = person(admin)
    stranger, _ = person(admin)
    outsider, _ = person(admin, "营销活动")
    try:
        ids = feedback(owner)
        draft = generate(owner, ids)
        assert (
            stranger.post(
                f"/api/questions/{ids[0]}/feedback/{ids[1]}/draft", headers=key()
            ).status_code
            == 404
        )
        assert stranger.get(f"/api/feedback-drafts/{draft['id']}").status_code == 404
        assert outsider.get(f"/api/feedback-drafts/{draft['id']}").status_code == 404
        assert stranger.get("/api/feedback-drafts?business=订单售后").json() == []
        assert outsider.get("/api/feedback-drafts?business=订单售后").status_code == 403
        pending = submit(owner, draft)
        stale = owner.put(
            f"/api/feedback-drafts/{draft['id']}",
            json={
                "version": 1,
                "content": draft["content"],
                "kind": "create",
                "status": "draft",
            },
        )
        assert stale.status_code == 409 and stale.json()["code"] == "VERSION_CONFLICT"
        wrong = publish(admin, submit(admin, generate(admin, feedback(admin, "营销活动"))))
        target = owner.put(
            f"/api/feedback-drafts/{draft['id']}",
            json={
                "version": pending["version"],
                "content": draft["content"],
                "kind": "revise",
                "status": "pending",
                "target_case_id": wrong["published_case_id"],
                "target_version": 1,
            },
        )
        assert target.status_code == 404
        forged = owner.put(
            f"/api/feedback-drafts/{draft['id']}",
            json={
                "version": pending["version"],
                "content": draft["content"],
                "kind": "revise",
                "status": "published",
            },
        )
        assert forged.status_code == 422
        with SessionLocal() as db:
            db.execute(update(User).where(User.id == owner_id).values(businesses=["营销活动"]))
            db.commit()
        assert (
            owner.post(
                f"/api/questions/{ids[0]}/feedback/{ids[1]}/draft", headers=key()
            ).status_code
            == 404
        )
        with TestClient(app) as anonymous:
            assert anonymous.get(f"/api/feedback-drafts/{draft['id']}").status_code == 401
    finally:
        owner.close()
        stranger.close()
        outsider.close()


def test_publication_requires_submission_and_manual_verification(admin: TestClient) -> None:
    """已解决不会自动验证；未提交不可发布，缺失验证依据的发布失败不改变草稿。"""
    draft = generate(admin, feedback(admin))
    before_submit = admin.post(
        f"/api/feedback-drafts/{draft['id']}/publish",
        json={
            "version": 1,
            "validity": "verified",
        },
        headers=key(),
    )
    assert before_submit.status_code == 409
    pending = submit(admin, draft, content=draft["content"])
    invalid = admin.post(
        f"/api/feedback-drafts/{draft['id']}/publish",
        json={
            "version": pending["version"],
            "validity": "verified",
        },
        headers=key(),
    )
    assert invalid.status_code == 422 and invalid.json()["code"] == "VERIFICATION_REQUIRED"
    assert admin.get(f"/api/feedback-drafts/{draft['id']}").json()["version"] == pending["version"]
    published = publish(admin, pending, validity="unverified")
    case = admin.get(f"/api/cases/{published['published_case_id']}").json()
    assert case["validity"] == "unverified"


def test_model_failure_retry_and_permission_recheck(
    admin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """生成失败不留半成品，重试保留原反馈；等待期间撤权不得保存模型正文。"""
    owner, owner_id = person(admin)
    try:
        ids = feedback(owner, outcome="unresolved")
        monkeypatch.setattr(
            feedback_generation,
            "active_connection",
            lambda db: ModelConnection(
                address="https://model.invalid/v1",
                api_key="test-only",
                model="test-model",
                managed=False,
            ),
        )

        def unavailable(*args: object) -> DraftContent:
            raise BusinessError("MODEL_UNAVAILABLE", "测试模型不可用", 502)

        monkeypatch.setattr(feedback_generation, "model_json", unavailable)
        endpoint = f"/api/questions/{ids[0]}/feedback/{ids[1]}/draft"
        retry_key = key()
        assert owner.post(endpoint, headers=retry_key).status_code == 502
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(FeedbackDraft)
                    .where(FeedbackDraft.feedback_id == ids[1])
                )
                == 0
            )
        monkeypatch.setattr(
            feedback_generation,
            "model_json",
            lambda *args: DraftContent(
                title="待确认的模型草稿",
                symptom="实际问题仍未解决",
                investigation="已核对但未恢复",
            ),
        )
        generated = owner.post(endpoint, headers=retry_key)
        assert generated.status_code == 201
        assert generated.json()["status"] == "draft"
        assert generated.json()["evidence"]["feedback"]["outcome"] == "unresolved"
        next_ids = feedback(owner)

        def revoke(*args: object) -> DraftContent:
            with SessionLocal() as db:
                db.execute(update(User).where(User.id == owner_id).values(businesses=[]))
                db.commit()
            return DraftContent(title="不可泄露的草稿", symptom="权限已撤销")

        monkeypatch.setattr(feedback_generation, "model_json", revoke)
        denied = owner.post(
            f"/api/questions/{next_ids[0]}/feedback/{next_ids[1]}/draft", headers=key()
        )
        assert denied.status_code == 404 and "不可泄露" not in denied.text
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(FeedbackDraft)
                    .where(FeedbackDraft.feedback_id == next_ids[1])
                )
                == 0
            )
    finally:
        owner.close()


def test_concurrent_generation_and_publication_do_not_duplicate(
    admin: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """不同请求键并发整理同一反馈只产生一条草稿，并发发布最多落地一个正式案例。"""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    ids = feedback(admin)
    barrier = Barrier(2)
    connection = ModelConnection(
        address="https://model.invalid/v1", api_key="test-only", model="test-model"
    )
    monkeypatch.setattr(feedback_generation, "active_connection", lambda db: connection)

    def respond(*args: object) -> DraftContent:
        barrier.wait(timeout=10)
        return DraftContent(title="合成并发回流", symptom="合成并发整理现象")

    monkeypatch.setattr(feedback_generation, "model_json", respond)

    def request(
        path: str, data: dict[str, object] | None = None
    ) -> tuple[int, dict[str, JsonValue]]:
        with TestClient(app) as browser:
            browser.cookies.update(admin.cookies)
            result = browser.post(path, json=data, headers=key())
            return result.status_code, result.json()

    # 1. 两次外部生成都结束后竞争存储唯一反馈约束，失败事务读取胜出草稿。
    path = f"/api/questions/{ids[0]}/feedback/{ids[1]}/draft"
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: request(path), range(2)))
    assert first[0] == second[0] == 201
    assert first[1]["id"] == second[1]["id"]
    draft = submit(admin, first[1])
    # 2. 发布用草稿版本条件认领事务，另一请求不得重复创建案例。
    path = f"/api/feedback-drafts/{draft['id']}/publish"
    payload = {"version": draft["version"], "validity": "verified"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: request(path, payload), range(2)))
    assert sorted(result[0] for result in results) == [200, 409]
    stored = admin.get(f"/api/feedback-drafts/{draft['id']}").json()
    assert stored["version"] == 3 and len(stored["history"]) == 3
    assert stored["published_case_version"] == 1
