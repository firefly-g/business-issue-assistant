"""装配应用生命周期、资源路由和公开错误，业务模块不导入 HTTP 启动入口。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from .api import auth, cases, materials, model_settings, questions, system
from .api.errors import install_error_handlers
from .api.middleware import RequestMiddleware
from .application.identity import bootstrap_admin
from .contracts.responses import ErrorRead


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """只初始化缺失管理员，数据库结构必须预先经过 Alembic 迁移。"""
    bootstrap_admin()
    yield


def create_app() -> FastAPI:
    """创建独立 HTTP 应用装配，不在创建阶段查询或修改业务数据。"""
    app = FastAPI(
        title="业务问题助手",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    install_error_handlers(app)
    app.add_middleware(RequestMiddleware)
    router = APIRouter(
        prefix="/api",
        responses={
            status: {"model": ErrorRead} for status in (401, 403, 404, 409, 413, 422, 500, 502)
        },
    )
    for module in (auth, cases, materials, questions, system, model_settings):
        router.include_router(module.router)
    app.include_router(router)
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app
