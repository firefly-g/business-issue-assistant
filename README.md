# 业务问题助手

将个人微信业务群中的问题、排查过程与解决经验整理成团队案例库，通过独立网页帮助业务同事查找经验、分析问题和反馈处理结果。

第一期前后端工程支持登录、业务范围权限、原始材料收录、草稿确认发布、关键词检索、问题分析、处理反馈及案例版本追溯。前端采用 React、TypeScript、Vite、Ant Design、Zustand、UnoCSS、React Router 和 Axios；后台采用 FastAPI、Pydantic、SQLAlchemy 和 Alembic。

## 本地启动

需要 Node.js 22.12+、npm 11+、Python 3.12+ 和 uv。当前复验使用 Node.js 24.19.0、npm 11.17.0，分别记录于 `.node-version` 与 `packageManager`。在项目根目录执行以下命令安装锁定依赖并初始化数据库。

```bash
npm ci
npm run setup:api
npm run seed
```

`npm run seed` 显式导入 4 条带有“虚构示例”标记的演示案例，可重复执行。希望从空案例库开始时，可以省略此步。

打开两个终端，分别启动后台与前端。

```bash
npm run api
```

```bash
npm run dev
```

打开 <http://127.0.0.1:5173>。本地默认邮箱为 `admin@example.com`，密码为 `local-dev-2026`。账号名称为“知识维护人”，可访问订单售后、营销活动、系统支持三个初始业务。用户邮箱、名称、密码及角色可通过配置和用户创建接口调整。

交互式接口文档位于 <http://127.0.0.1:8000/api/docs>。前端开发服务器将 `/api` 代理到后台，登录 Cookie 与网页保持同源。先执行 `npm run build`，再启动后台时，后台也会直接提供构建后的网页，地址为 <http://127.0.0.1:8000>。

## 配置

将 `backend/.env.example` 复制为 `backend/.env` 后修改。SQLite 为默认本地数据库，数据与上传图片保存在 `backend/data/`，这些内容已加入 Git 忽略规则。

```bash
cp backend/.env.example backend/.env
```

管理员仅在首次初始化时创建。已有数据库的管理员信息不会随环境变量变化自动覆盖。登录会话有效期为 7 天，退出后服务端会话失效。身份仅从服务端 Cookie 会话恢复；切换账号会清空 Zustand 中的业务选择和复用输入，不持久化口令或令牌。

知识维护人可在工作台的「模型配置」保存多套模型连接。点击「新增模型」，填写 HTTPS 基础地址和 API 密钥，获取供应商目录并选择模型。连接测试通过后点击「保存配置」，即可将它加入列表。点击列表中某一项的「启用」后，团队后续的问题分析和草稿整理采用该配置。每次只启用一套，其他配置可随时切换。「切换为本地规则」停用模型辅助并保留列表。

供应商目录要求兼容 `GET /models`，实际结构化对话能力以连接测试为准。已保存的密钥只显示配置状态。使用相同地址可留空复用已有密钥，改变地址时需重新填写。旧版已配置的模型在数据库升级后自动加入列表并保留原运行状态。

网页连接测试仅发送固定测试内容，连接限公网 HTTPS 标准端口。自建内网模型仍可在服务端用以下环境变量配置。部署配置完整时，列表显示一项「环境变量」模型，可在网页中选择启用。

```dotenv
MODEL_BASE_URL=https://your-model-gateway.example/v1
MODEL_API_KEY=填写模型服务密钥
MODEL_NAME=填写模型名称
```

接口地址会拼接 `/chat/completions`，服务需支持 `messages`、`response_format` 的 JSON 对象输出及 `choices[0].message.content` 返回结构。后台校验结构化结果，引用范围和发布状态由业务服务控制。接口故障会返回可重试错误，当前表单输入保留。外部模型服务需要使用实际供应商配置验证。

模型配置全部留空时使用本地规则模式，环境变量部分填写会在启动时拒绝。网页保存的 API 密钥在数据库中加密。本地开发首次使用时创建 `backend/data/model-settings.key`。正式部署需在服务端配置 `MODEL_SETTINGS_KEY`，可用 `cd backend && uv run python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` 生成并放入部署密钥存储。共享数据库的服务实例使用同一份加密密钥，备份时单独保管。

本地模式按中文双字和完整错误码检索，草稿预览仅提取标题与原文，其余字段由处理人补充。图片目前作为原始依据保存和查看，分析时请补充图片关键文字。

需要使用 PostgreSQL 时，先启动数据库，再调整后台数据库地址并执行迁移。

```bash
docker compose up -d db
```

```dotenv
DATABASE_URL=postgresql+psycopg://assistant:assistant_local_only@127.0.0.1:5432/assistant
```

```bash
npm run setup:api
```

`compose.yaml` 提供本地 PostgreSQL 服务与持久卷。通过 `POSTGRES_PASSWORD` 调整数据库密码时，需同步更新连接地址。部署环境设置 `APP_ENV=production`、独立的 `ADMIN_PASSWORD`，在 HTTPS 下启用 `COOKIE_SECURE=true`。

## 当前业务流程

1. 登录后选择业务，在“收录经验”中保存原始聊天及可选图片。
2. 校正草稿并提交，草稿初始状态为待确认、待验证。
3. 问题处理人或知识维护人补充适用条件、处理步骤与实际验证记录，确认方案有效性。
4. 知识维护人发布案例。在“问题助手”中提问时，仅将本业务内已发布且已验证的案例作为参考。
5. 从案例详情查看原始依据和历史版本，完成处理后保存实际反馈。

知识维护人可以通过 `POST /api/users` 创建业务同事、问题处理人和知识维护人账号，并配置业务范围。用户列表及账号管理页面后续接入。重复提交草稿、分析及反馈时沿用同一 `Idempotency-Key`，服务端返回第一次成功的结果；权限撤销后仍须重新授权。编辑案例需要携带版本号，并发版本冲突返回 409，界面保留本地草稿供人工核对。

React Router 使用 Hash 路由，无需额外配置服务器路径回退。业务、案例搜索、验证筛选和案例详情编号由 URL 保存，可刷新恢复；Zustand 只保存账号范围内的客户端选择。常规请求统一经过“页面或业务 Hook → 领域 Service → Axios Client”，不再使用 `fetch`。Axios 集中处理同源 Cookie、60 秒超时、取消和错误归一化，写请求不自动重试；取消浏览器等待不代表后台操作已撤销。

## 工程结构

```text
frontend/
  src/
    app/               # 应用装配、会话守卫、布局与路由
    api/services/      # 按身份、案例、分析、材料和统计划分的领域接口
    api/client.ts      # 唯一 Axios 传输入口
    api/generated.ts   # 从实际 OpenAPI 生成的类型，不手工修改
    api/contract.json  # 同源生成的响应运行时校验规则
    store/             # 会话与工作台 Zustand 状态
    pages/             # 按业务拆分的页面、Hook 和私有交互
    hooks/             # 查询取消、晚到响应隔离和写请求范围
    components/        # 跨页面复用的交互与错误恢复
  uno.config.ts        # UnoCSS 预设与语义快捷类
backend/
  app/
    factory.py         # FastAPI 工厂与生命周期装配
    api/               # Router、依赖、错误映射与请求上下文
    application/       # 授权、幂等、事务和业务用例
    domain/            # 有限状态、命令、可信身份与人工确认规则
    contracts/         # 输入校验与安全响应投影
    models.py          # SQLAlchemy 存储模型
    provider.py        # 外部模型适配、超时和结果校验
  alembic/             # 数据库迁移
  rules/               # 版本化的收录与分析规则
  scripts/             # 契约导出和临时 PostgreSQL 验证
  tests/               # 业务、授权、配置、契约和旧库升级验证
  openapi.json         # 从实际路由生成的公开契约
compose.yaml           # 本地 PostgreSQL 服务
```

## 验证命令

```bash
npm run check
npm run check:postgres
```

`npm run check` 依次执行契约漂移、Prettier、ESLint、TypeScript、Vitest、生产构建、Ruff、mypy strict、pytest 与 Alembic 模型漂移检查。`npm run check:postgres` 需要 Docker，会创建随机命名、随机口令和回环随机端口的 PostgreSQL 17 临时容器，执行完整后端测试后清理，不使用开发数据库卷。常规 pytest 默认使用隔离的临时 SQLite。

接口或 Schema 变更后执行 `npm run contract:generate`，提交 OpenAPI、运行时 Schema 与生成类型；CI 或本地用 `npm run contract:check` 检查漂移。前端 Service 在交付响应前使用同源 JSON Schema 校验未知数据，静态类型不替代运行时验证。

本轮规范执行范围、实际验收与未验证环境见 [规范执行记录](docs/规范执行记录.md)。

## 后续实施范围

企业单点登录、图片 OCR、向量检索、案例合并、结案自动转草稿、固定业务评估集和后台任务队列继续按文档推进。第二期微信采集与第三期 Agent 编排按规划独立实施。当前初始业务分类用于工程验证，正式试点时结合真实业务调整。

## 文档入口

| 文档 | 内容 |
| --- | --- |
| [完整规划文案](docs/业务问题与解决方案平台-规划文案.md) | 产品定位、页面与流程、案例字段、三期范围、技术建议及验收标准 |
| [开发路线与待办](docs/开发路线与待办.md) | 每期交付内容、前置条件和验收清单 |
| [试点信息填写模板](docs/试点信息填写模板.md) | 试点业务、常见问题、试用人员和真实案例填写位置 |
| [项目决策记录](docs/项目决策记录.md) | 当前方向、建议技术栈及需要进一步确认的事项 |
| [规范执行记录](docs/规范执行记录.md) | 规范采用差异、工程整改、检查结果及验收边界 |

## 分期建设

1. 第一期：独立网页、案例收录、人工确认、检索与 AI 辅助分析。
2. 第二期：本地微信辅助收集，先验证一键导入，再评估指定群定时采集。
3. 第三期：自建业务排查 Agent，复用既有接口、案例和规则，支持动态追问与多步排查。

第一期即落实接口复用、来源与数据版本、独立规则和评估记录。AI 整理结果先作为草稿，方案是否验证有效由实际处理人确认。

## 当前技术栈与后续选型

- 前端：React、TypeScript、Vite、Ant Design、Zustand、UnoCSS、React Router、Axios，已落实。
- 后台：Python、FastAPI、Pydantic。
- 数据：PostgreSQL、SQLAlchemy、Alembic；按检索效果引入 pgvector。
- 文件：云对象存储；本地开发使用文件目录。
- 任务：耗时处理进入正式试点时引入 Celery、Redis。
- 采集：运行在登录微信的电脑上的独立工具，通过 HTTPS 接入平台。
- Agent：第三期评估采用 LangGraph，配置持久化运行状态。
- 部署：Linux、Docker Compose，结合现有托管数据库和对象存储条件选择。

已安装依赖的具体版本以锁文件为准；对象存储、任务队列、采集工具、Agent 和部署环境仍按试点需求确认。

## 试点准备

填写试点信息模板，提供至少一个包含实际处理结果的真实案例，再据此确定页面原型、数据字段和第一期接口。虚构示例用于说明填写方式，不作为已验证的业务知识。

## 文档维护

后续规划以本项目目录中的文档为准。完整规划文案从原讨论目录复制，原文件保留作为历史备份；本项目创建日期为 2026 年 11 月 16 日。
