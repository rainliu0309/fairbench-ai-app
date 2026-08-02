# Fair Bench｜公允准鉴

> **A governed, traceable workflow for assessing facial-recognition fairness.**<br>
> 为公共人工智能算法监管提供可追溯的人脸识别公平性评测工作流。

### 🚀 [Live Demo · 在线体验](https://fairbench-ai-app.onrender.com)

Fair Bench 面向公共人工智能监管机构，提供覆盖测试图集管理、人口属性标注、外部人脸识别接口评测、公平性指标分析和审计归档报告生成的一体化监管工作台。平台不训练或提供人脸识别模型，仅对接并评测待审算法，以可追溯、可复核的方式支持监管评估。

Fair Bench is a self-hosted fairness-audit platform for public AI regulators. It
provides an integrated workflow for test dataset management, demographic
annotation, external facial-recognition API evaluation, fairness metric analysis,
and bilingual archival PDF generation. The platform does not train or provide
facial-recognition models; it evaluates submitted algorithms through a traceable,
reviewable regulatory process.

[中文](#中文) · [English](#english)

---

## 中文

### 四步监管评测流程

| 步骤 | 页面 | 用途 |
| --- | --- | --- |
| 1. 测试图集管理 | `/datasets` | 批量上传 JPG、PNG、WebP 人脸样本；调用 Agnes 人口属性标注，并可在需要时进行人工复核 |
| 2. 评测任务面板 | `/tasks` | 选择已就绪图集，配置待测人脸识别接口、临时密钥、请求映射与公平阈值，异步发起批量评测 |
| 3. 公平性数据看板 | `/dashboard` | 查看整体准确率、群体准确率差值、公平偏差系数、标准差及多算法横向比较 |
| 4. 审计报告 | `/reports` | 选择归档内容、报告语言及签发信息，预览并生成可下载的政务审计 PDF |

默认首页为 `/workspace`，以监管流程、当前资产与快捷入口引导审核人员完成上述操作。
本地单用户模式中，使用预置本地监管管理员一键进入；共享或生产环境可关闭该模式，
通过初始化登录页创建首位管理员。

### 架构铁则

本项目将“受评算法”“标注服务”“评测计算”和“审计证据”明确隔离：

- 平台不自研、不托管、不替代任何人脸识别模型；识别结果只来自每个评测任务配置的外部 API；
- Agnes 仅用于授权评测样本的人口属性分组：年龄段、性别、族裔及置信度；它不决定评测结论；
- 样本图像存入 S3 兼容对象存储（本地 MinIO、线上 Supabase Storage），对象引用与业务记录存入 PostgreSQL，批量标注和评测由 Redis + ARq 执行；
- 每次厂商调用均有超时、并发限制、重试与失败隔离；失败样本可单独查看并重新发起；
- 目标 API 密钥只在 Redis 临时缓存中保存并设置 TTL；PostgreSQL 仅保存不可逆指纹用于审计关联；
- 操作日志由 `previous_hash` 与 `entry_hash` 构成链式记录；应用层与 PostgreSQL 触发器拒绝修改或删除；
- 指标计算位于独立服务中，使用 Pandas 与 NumPy，便于新增公平性标准而不改动厂商适配层；
- 报告编号、报告摘要与生成记录会进入审计链，报告 PDF 归档至 S3 兼容对象存储。

完整链路如下：

```text
监管审核人员
      │
React + TypeScript + Vite ── REST / 进度轮询 ── FastAPI
      │                                              │
      │                             ┌────────────────┼──────────────────┐
      │                             │                │                  │
      │                        PostgreSQL         Redis          S3 兼容存储
      │                    业务记录 + 审计链      临时密钥 + ARq      图像 + PDF
      │                                              │
      └────────────────────────── ARq Worker ────────┼───────┐
                                                     │       │
                                               Agnes 标注 API  待测人脸识别 API
                                                     │       │
                                           Pandas / NumPy 指标计算
                                                     │
                                               WeasyPrint 双语报告
```

### Agnes 与待测接口对接

Agnes 标注在创建图集时自动执行。根目录 `.env` 提供两种适配方式：

- `multipart_attributes`：将图片以 multipart 表单发送至一个直接返回属性 JSON 的接口；
- `openai_vision`：将图片发送至 OpenAI-compatible vision chat-completions 接口，要求模型返回严格的分组 JSON。

使用 Agnes OpenAI-compatible vision 接口时，填写如下配置（密钥只应保存在本机或部署平台的密钥管理中）：

```dotenv
AGNES_API_URL=https://apihub.agnes-ai.com/v1/chat/completions
AGNES_API_KEY=your_server_side_key
AGNES_AUTH_SCHEME=bearer
AGNES_AUTH_HEADER=Authorization
AGNES_PROVIDER_MODE=openai_vision
AGNES_MODEL=agnes-2.0-flash
```

若使用直接返回人口属性的服务，请保留 `AGNES_PROVIDER_MODE=multipart_attributes`，并按对方响应结构配置
`AGNES_RESPONSE_AGE_PATH`、`AGNES_RESPONSE_GENDER_PATH`、`AGNES_RESPONSE_ETHNICITY_PATH` 与
`AGNES_RESPONSE_CONFIDENCE_PATH`。这些字段支持点路径，例如 `data.demographics.age_group`。

待测人脸识别接口在“新建评测任务”中配置。通用适配器会以 multipart 发送图片和基准身份，
并从厂商 JSON 中读取 `predicted_identity`、`confidence` 与可选的 `is_correct`。请求字段、静态字段、
认证头、响应点路径、超时和重试次数均可按任务设定。签名请求、OAuth 刷新令牌、异步回调或
JSON/base64 等非 multipart 协议，应在 `backend/services/target_api_service.py` 增加专用适配器后再用于正式评测。

### 技术栈

- **前端：** React 19、TypeScript、Vite、React Router、TanStack Query、Recharts、i18next、Axios；
- **后端：** Python 3.12、FastAPI、SQLAlchemy Async ORM、Pydantic、OpenAPI；
- **数据与任务：** PostgreSQL 16、Redis 7、ARq、Pandas、NumPy；
- **文件与报告：** S3 兼容存储（MinIO / Supabase Storage）、Jinja2、WeasyPrint；
- **外部服务：** Agnes 人口属性标注适配器、可配置的目标人脸识别 API 适配器；
- **本地演示：** Docker Compose 同时启动 PostgreSQL、Redis、MinIO、FastAPI、ARq Worker、前端和内部 HTTP 合约模拟器。

### 项目结构

```text
fairbench-ai-app/
├── frontend/
│   ├── src/
│   │   ├── api/                 # Axios 客户端、接口调用与数据契约
│   │   ├── assets/              # 全局政务后台样式与静态资源
│   │   ├── components/          # 图集、任务、看板、报告及通用组件
│   │   ├── i18n/locales/        # zh.json / en.json 双语资源
│   │   ├── layouts/             # GovLayout 政务后台布局
│   │   ├── store/               # 浏览器会话状态
│   │   └── views/               # 工作台、图集、任务、看板、报告、登录
│   ├── Dockerfile
│   └── package.json
├── backend/
│   ├── api/                     # auth、dataset、task、stats、report、audit 路由
│   ├── core/                    # 配置、数据库、安全和双语后端文案
│   ├── models/                  # SQLAlchemy 数据表模型
│   ├── queue/                   # ARq worker 任务定义
│   ├── schemas/                 # Pydantic 请求与响应模型
│   ├── services/                # Agnes、目标 API、指标、存储、报告、审计服务
│   ├── templates/               # WeasyPrint 双语 PDF 模板
│   ├── tests/                   # 指标计算测试
│   ├── main.py                  # FastAPI 应用入口
│   └── simulator_main.py        # 内部 HTTP 合约测试模拟器
├── demo_data/                   # 36 份合成样本、清单与可重复生成脚本
├── test/                        # 本地端到端测试用 16 张图片样本
├── docker-compose.yml
├── Dockerfile.render-free       # Render 免费单服务生产镜像
├── render.yaml                  # 默认免费 Blueprint
├── render.paid.yaml             # 可选的资源分离付费 Blueprint
├── .env.example
├── LICENSE
└── README.md
```

### 本地启动

前置条件：Docker Desktop（含 Docker Compose v2）。非 Docker 后端开发需 Python 3.12；
前端单独开发需 Node.js 20 或更高版本。

```bash
cp .env.example .env
docker compose up --build
```

启动后访问：

- 管理后台：<http://localhost:5173>
- OpenAPI / Swagger：<http://localhost:8000/docs>
- FastAPI 健康检查：<http://localhost:8000/health>
- MinIO Console：<http://localhost:9001>

首次本地启动若未创建 `.env`，Compose 会启用一套合成图集、示例任务和内部模拟服务，
便于验证全链路。若已经复制 `.env` 并要进行自己的真实测试，请将
`SEED_DEMO_DATA=false`，再填写 Agnes 与待测厂商配置。

停止服务：

```bash
docker compose down
```

只有明确希望清空本地 PostgreSQL、Redis 和 MinIO 演示数据时，才添加 `-v`。

### 环境变量

先复制 [`.env.example`](.env.example)，再按部署环境修改。以下默认值仅适合本地开发，
不能直接用于共享或生产环境。

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `fairbench` / `fairbench` / 开发密码 | PostgreSQL 初始化信息 |
| `DATABASE_URL` | Compose 内 PostgreSQL 地址 | 后端异步数据库连接 |
| `REDIS_URL` | `redis://redis:6379/0` | ARq 队列与临时 API 密钥缓存 |
| `MINIO_ENDPOINT` / `MINIO_*` | Compose 内 MinIO | 图像和 PDF 对象存储 |
| `S3_ENDPOINT_URL` / `S3_*` | 空（回退到 MinIO） | 线上 S3 兼容对象存储；Supabase 端点需保留 `/storage/v1/s3` |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | `3` / `2` | 数据库连接池上限控制 |
| `WORKER_MAX_JOBS` | `4` | 单个 ARq Worker 最大并发任务数；免费部署设为 `1` |
| `AGNES_API_URL` | 示例地址 | Agnes 或兼容标注服务地址 |
| `AGNES_API_KEY` | 空 | 仅服务端读取的标注服务密钥 |
| `AGNES_PROVIDER_MODE` | `multipart_attributes` | `multipart_attributes` 或 `openai_vision` |
| `AGNES_MODEL` | `agnes-2.0-flash` | vision-chat 适配模式下的模型名称 |
| `AGNES_MAX_RETRIES` / `AGNES_MAX_CONCURRENCY` | `2` / `4` | Agnes 调用重试与并发上限 |
| `API_SECRET_TTL_SECONDS` | `86400` | 待测 API 密钥在 Redis 中的最长存活时间（秒） |
| `JWT_SECRET` | 必须替换 | 共享环境的签名密钥，至少 32 个字符 |
| `LOCAL_SINGLE_USER_MODE` | `true` | 本机一键管理员会话；共享环境应设为 `false` |
| `LOCAL_ADMIN_EMAIL` / `LOCAL_ADMIN_DISPLAY_NAME` | 本地管理员 | 本地单用户模式的默认管理员资料 |
| `SEED_DEMO_DATA` | `.env` 中为 `false` | 是否写入合成演示图集和任务 |
| `MAX_UPLOAD_FILES` / `MAX_UPLOAD_FILE_BYTES` | `200` / `15 MiB` | 单批上传文件数与单文件大小限制 |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | 浏览器访问后端 API 的基础地址 |

不要把 `AGNES_API_KEY`、待测厂商密钥或 `JWT_SECRET` 提交到 Git，也不要使用 `VITE_`
前缀暴露任何服务端密钥。

### REST API 与 OpenAPI

API 基础路径为 `/api/v1`，并在 <http://localhost:8000/docs> 自动生成交互式 OpenAPI
文档。核心接口如下：

| 方法 | 路径 | 职责 |
| --- | --- | --- |
| `POST` | `/auth/local-session` | 本地单用户模式签发管理员会话 |
| `POST` | `/auth/bootstrap` | 非单用户环境初始化首位管理员 |
| `POST` | `/auth/login` | 管理员登录 |
| `GET` / `POST` | `/datasets` / `/datasets/upload` | 图集列表与批量上传、异步标注 |
| `PATCH` | `/datasets/{dataset_id}/samples/{sample_id}/label` | 保存可追溯的人工标签修正 |
| `GET` | `/datasets/{dataset_id}/export.csv` | 导出样本原始数据 |
| `GET` / `POST` | `/tasks` | 查看或创建异步评测任务 |
| `GET` / `POST` | `/tasks/{task_id}/failed-samples` / `/retry-failed` | 查看失败样本与重试 |
| `GET` | `/tasks/{task_id}/results.csv` | 导出评测结果 CSV |
| `GET` | `/stats/overview`、`/stats/tasks/{task_id}`、`/stats/compare` | 获取看板与横向比较指标 |
| `POST` / `GET` | `/reports`、`/reports/{report_id}/download` | 生成及下载归档报告 |
| `GET` | `/audit-logs` | 查询操作审计链 |

常规业务响应带有双语 `message`，并通过 `X-Request-ID` 支持链路追踪。所有 API 访问均会
进入操作日志；发生业务变更时还会写入更详细的领域审计事件。

### 完整功能测试

仓库中的 [`test/`](test/) 包含 16 张可用于本地端到端测试的图片。建议按以下顺序进行：

1. 将 Agnes 配置填入 `.env`，执行 `docker compose up --build`；
2. 在“测试图集管理”创建图集并上传 `test/` 中的图片；
3. 等待标注完成；若个别样本失败，可在图集详情中人工复核，填写年龄组、性别、族裔、基准身份和修正原因；
4. 在“评测任务面板”选择该图集，填写待测厂商接口地址、认证方式、临时密钥和请求/响应映射；
5. 创建任务后观察实时进度；在失败样本抽屉中核查失败代码并按需重试；
6. 在“公平性数据看板”选择任务，检查群体准确率、最大群体差值、偏差系数及告警；
7. 在“审计报告”填写签发机构、审核签发人和报告语言，确认预览内容后生成 PDF。

如只需验证平台 HTTP、队列、失败隔离和报告流程，可在任务中使用 Compose 内部模拟器默认地址
`http://simulator:8080/v1/face/recognize`，认证方式选择“无需认证”。该地址只在 Docker
内部网络可访问；免费 Render 镜像会把表单默认地址替换为同容器的 `127.0.0.1` 模拟器。
二者都只用于合约流程测试，不应作为真实厂商识别能力或对外服务地址。

### 质量检查与本地开发

后端测试与前端生产构建：

```bash
cd backend
python -m pytest

cd ../frontend
npm install
npm run build
```

前端热更新开发：

```bash
cd frontend
npm run dev
```

如需脱离 Compose 调试后端，请先保证 PostgreSQL、Redis 和 MinIO 可访问，然后：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload
```

另开终端启动任务 Worker：

```bash
cd backend
arq worker_settings.WorkerSettings
```

### 部署与生产检查

`docker-compose.yml` 适合本地演示、功能验收和受控测试。部署到共享、测试或生产环境前，
至少应完成以下事项：

- 关闭 `LOCAL_SINGLE_USER_MODE`，设置唯一的 `JWT_SECRET`，并接入组织身份认证与最小权限 RBAC；
- 设置 `SEED_DEMO_DATA=false`，替换全部数据库、MinIO 与服务端默认密码，并使用正式密钥管理服务注入环境变量；
- 在可信反向代理后启用 TLS、HSTS、网络白名单、上传恶意文件扫描、限流与监控告警；
- 根据适用辖区配置数据保留、删除、备份、对象锁/WORM 与灾难恢复策略；
- 由主管机构审定人口分类、指标口径、公平阈值、报告模板和人工复核流程；
- 在处理真实生物特征数据前完成数据保护影响评估（DPIA/PIA）、安全测试和法律合规审批；
- 在将结果作为正式监管结论前，对接入厂商接口、样本来源、标签质量、阈值和评测方法进行独立复核。

### Render 免费部署

根目录的 [`render.yaml`](render.yaml) 是默认免费 Blueprint。它只创建一个 Render Free Web
Service：同一容器提供 React 静态页面、FastAPI、低并发 ARq Worker 与内部合约测试模拟器。
持久化 PostgreSQL 和 S3 对象存储使用 Supabase Free，队列与临时密钥缓存使用 Upstash Redis
Free，因此不会请求 Render 付费实例。前端与 API 同源，所有服务端密钥仅作为 Render 环境变量注入。

部署前先准备以下三组信息，任何密钥都不要提交到 Git：

1. 在 Supabase 创建 Free 项目；在 Storage 新建私有 bucket `fairbench-assets`；
2. 在 Supabase Storage 的 S3 设置中生成 Access Key，记录 Endpoint、Region、Access Key ID 和
   Secret Access Key。Endpoint 必须是完整的 `https://<project-ref>.storage.supabase.co/storage/v1/s3`；
3. 在 Supabase 的 **Connect** 面板复制 **Session pooler** PostgreSQL URL，保留 SSL 参数；若密码
   含特殊字符，使用面板提供的已编码连接串；
4. 在 Upstash 创建 Free Redis 数据库，复制以 `rediss://` 开头的 TLS 连接串；
5. 登录 Render，选择 **New → Blueprint**，连接 `rainliu0309/fairbench-ai-app`，分支选择 `main`；
6. 在创建表单中填写 `DATABASE_URL`、`REDIS_URL`、`S3_ENDPOINT_URL`、`S3_ACCESS_KEY`、
   `S3_SECRET_KEY`、`S3_REGION`、`AGNES_API_URL` 与 `AGNES_API_KEY`，然后应用 Blueprint；
7. 服务变为 **Live** 后打开其 `onrender.com` 地址，访问 `/health` 确认 `status: ok`，再以默认
   管理员进入并上传测试图集。

`render.yaml` 已启用 Git 自动部署：以后推送到 `main` 会自动重新构建并发布。Render Free 服务
空闲后会休眠，首次访问需要等待冷启动；进行标注或评测时前端进度轮询会保持服务活跃。Supabase、
Upstash 与 Render 的免费额度和停用政策可能变化，正式处理大规模或受监管数据前应升级并配置备份、
WORM/对象锁、监控和组织级身份认证。

为了演示便利，免费 Blueprint 默认启用 `LOCAL_SINGLE_USER_MODE=true` 且不自动写入合成数据。
部署给外部机构或处理真实数据前，应关闭单用户模式并接入组织身份认证。原先前端、API、Worker、
PostgreSQL、Redis、MinIO 分离的付费拓扑保存在 [`render.paid.yaml`](render.paid.yaml)；需要时将其
内容替换根 `render.yaml` 后再创建付费 Blueprint。

### 隐私、审计与使用边界

- 仅上传具有合法授权、明确用途和适当数据处理依据的图像；
- 平台的合成 `demo_data/` 仅用于软件流程演示，不能用于证明真实算法性能；
- 手工修正会记录修正前后标签、原因、操作者和时间，作为不可删除的审计事件；
- 不要把 API 密钥放入图集名称、文件名、描述、URL 参数或日志；
- 失败样本不计入准确率分母，会单独归档与展示；
- 公平性指标是监管评测证据的一部分，不应脱离样本代表性、标签质量、适用法律和人工审查单独解释。

### 版权声明

版权所有 © 2026 Rain Liu。保留所有权利。本项目为专有项目，使用限制请参阅
[LICENSE](LICENSE)。

---

## English

### Four-step oversight workflow

| Step | View | Purpose |
| --- | --- | --- |
| 1. Dataset management | `/datasets` | Batch-upload JPG, PNG, or WebP evaluation samples; obtain Agnes labels and make traceable reviewer corrections when required |
| 2. Evaluation tasks | `/tasks` | Select a ready dataset, configure the target API, temporary secret, request mapping, and fairness threshold, then start an asynchronous batch run |
| 3. Fairness dashboard | `/dashboard` | Review overall accuracy, demographic accuracy gaps, bias coefficient, standard deviation, alerts, and cross-algorithm comparisons |
| 4. Audit reports | `/reports` | Choose archival content, language, and signatory details; preview, generate, and download the formal PDF report |

The default landing route is `/workspace`. It explains the oversight sequence,
shows the current workspace state, and provides direct entry points. Local
single-user mode opens a trusted local regulator session; shared environments
can disable that mode and bootstrap the first administrator through the sign-in
screen.

### Non-negotiable architecture

- Fair Bench does not train, host, or substitute any facial-recognition model.
  Recognition results come only from the target API configured for an evaluation task.
- Agnes is used only to assign demographic groups to authorized evaluation samples;
  it does not determine an audit outcome.
- Image objects are stored in S3-compatible storage (local MinIO or managed
  Supabase Storage), business records in PostgreSQL, and batch
  annotation/evaluation work in Redis + ARq.
- Provider calls are bounded by timeouts, concurrency limits, retries, and
  per-sample failure isolation. Failed samples can be inspected and retried.
- Target API secrets exist only in Redis with a TTL. PostgreSQL stores a
  non-reversible fingerprint for audit correlation, never the secret itself.
- Audit records are hash chained through `previous_hash` and `entry_hash`.
  Application guards and a PostgreSQL trigger reject updates and deletes.
- Pandas and NumPy metric logic remains independent of the provider adapters,
  allowing future standards to be added without coupling to a vendor contract.
- Report identifiers, report summaries, and generation events are written to the
  audit trail; PDF archives are stored in S3-compatible object storage.

### Agnes and target API integration

The root [`.env.example`](.env.example) supports two demographic-annotation
modes:

- `multipart_attributes` submits an image as multipart form data to a service
  returning demographic JSON.
- `openai_vision` submits an image to an OpenAI-compatible vision
  chat-completions endpoint and requires strict JSON labels.

For an Agnes OpenAI-compatible vision endpoint, configure server-side values
such as:

```dotenv
AGNES_API_URL=https://apihub.agnes-ai.com/v1/chat/completions
AGNES_API_KEY=your_server_side_key
AGNES_AUTH_SCHEME=bearer
AGNES_PROVIDER_MODE=openai_vision
AGNES_MODEL=agnes-2.0-flash
```

For direct attribute APIs, configure the `AGNES_RESPONSE_*_PATH` values with
safe dot paths such as `data.demographics.age_group`.

The evaluation-task form configures the target recognition API. The standard
adapter sends a multipart image plus expected identity, then reads mapped
`predicted_identity`, `confidence`, and optional `is_correct` fields. Field
names, headers, static form values, authentication, response paths, timeouts,
and retry count are task-specific. Signed requests, OAuth refresh, async
callbacks, and JSON/base64-only providers need a dedicated adapter in
`backend/services/target_api_service.py` before formal use.

### Stack

- **Client:** React 19, TypeScript, Vite, React Router, TanStack Query,
  Recharts, i18next, and Axios.
- **API:** Python 3.12, FastAPI, SQLAlchemy async ORM, Pydantic, and OpenAPI.
- **Data and jobs:** PostgreSQL 16, Redis 7, ARq, Pandas, and NumPy.
- **Files and reporting:** S3-compatible storage (MinIO / Supabase Storage),
  Jinja2, and WeasyPrint.
- **Integrations:** Agnes demographic-annotation adapter and a configurable
  target-recognition API adapter.
- **Local integration environment:** Docker Compose runs PostgreSQL, Redis,
  MinIO, FastAPI, ARq Worker, frontend, and an internal HTTP contract simulator.

### Run locally

Prerequisite: Docker Desktop with Docker Compose v2. Standalone backend work
requires Python 3.12; standalone frontend work requires Node.js 20 or newer.

```bash
cp .env.example .env
docker compose up --build
```

Open the console at <http://localhost:5173>, Swagger/OpenAPI at
<http://localhost:8000/docs>, the health endpoint at
<http://localhost:8000/health>, and MinIO Console at <http://localhost:9001>.

When no `.env` exists, the Compose defaults start synthetic data and an internal
simulator for end-to-end verification. For your own controlled test, copy the
environment file, set `SEED_DEMO_DATA=false`, and configure Agnes plus the
target vendor contract. Stop services with `docker compose down`; add `-v` only
when intentionally erasing local PostgreSQL, Redis, and MinIO volumes.

### Environment variables

Copy [`.env.example`](.env.example) before configuring a deployment. The key
groups are database/object storage (`POSTGRES_*`, `DATABASE_URL`, `MINIO_*`,
`S3_*`),
queue and ephemeral secrets (`REDIS_URL`, `API_SECRET_TTL_SECONDS`), Agnes
(`AGNES_*`), local access (`JWT_SECRET`, `LOCAL_SINGLE_USER_MODE`,
`LOCAL_ADMIN_*`), fixture data (`SEED_DEMO_DATA`), upload controls (`MAX_UPLOAD_*`),
and browser API location (`VITE_API_BASE_URL`).

Never commit `AGNES_API_KEY`, a target-vendor secret, or `JWT_SECRET`. Never use
a `VITE_` prefix for a server secret because Vite publishes such values to the
browser build.

### REST API

The API lives beneath `/api/v1`, with interactive contracts generated at
`/docs`. It covers local/session authentication, dataset upload and labels,
asynchronous tasks and failed-sample retries, metric overview/comparison,
report preview/download, CSV exports, and audit-log queries. Every API request
receives an `X-Request-ID` and is added to the operation trail; domain mutations
also add detailed evidence events.

### End-to-end test

[`test/`](test/) includes 16 images for controlled local testing:

1. Configure Agnes and start Compose.
2. Upload the images through Dataset Management and wait for annotation.
3. Review any failed annotations, recording demographic labels, reference
   identity, and a correction reason.
4. Create an evaluation task with the target vendor endpoint, temporary key,
   authentication, and request/response mapping.
5. Inspect progress and failed samples, then retry when appropriate.
6. Review group metrics and alerts in the dashboard.
7. Configure the signer, language, and report content before generating the PDF.

For an HTTP/queue/report workflow check without an external vendor, use the
internal Compose-only simulator address
`http://simulator:8080/v1/face/recognize` with no authentication. It is not a
public endpoint and must not be presented as one. The free Render image replaces
the form default with its same-container `127.0.0.1` simulator; both endpoints
verify the integration contract only, not real recognition performance.

### Validate and develop

```bash
cd backend
python -m pytest

cd ../frontend
npm install
npm run build
```

For frontend hot reload, run `npm run dev` in `frontend/`. For standalone backend
debugging, create a Python virtual environment, install
`requirements-dev.txt`, run `uvicorn main:app --reload`, and start
`arq worker_settings.WorkerSettings` in a second terminal after PostgreSQL,
Redis, and MinIO are available.

### Free deployment on Render

The root [`render.yaml`](render.yaml) is the default free Blueprint. One Render
Free Web Service serves the React build and FastAPI API while also running a
single-concurrency ARq worker and the internal contract-test simulator. A free
Supabase project supplies PostgreSQL and private S3-compatible Storage; a free
Upstash database supplies TLS Redis for ARq and expiring target-API secrets.

1. Create a Supabase Free project and a private `fairbench-assets` Storage bucket.
2. Generate Supabase S3 access keys and retain the complete endpoint ending in
   `/storage/v1/s3`, region, access key ID, and secret access key.
3. Copy the Supabase **Session pooler** PostgreSQL connection string from the
   Connect panel, including its SSL parameter.
4. Create an Upstash Free Redis database and copy its `rediss://` TLS URL.
5. In Render choose **New → Blueprint**, connect `rainliu0309/fairbench-ai-app`,
   and select `main`.
6. Supply the prompted database, Redis, S3, and Agnes environment variables,
   then apply the Blueprint.
7. When the service is Live, verify `/health`, open the site, and sign in with
   the default administrator session.

Commits pushed to `main` deploy automatically. Free Render services sleep when
idle, so the first request can have a cold-start delay; active assessment
polling keeps the service awake while a job is running. Provider free-tier
quotas and inactivity policies can change and are not a substitute for the
backups, object retention, monitoring, and identity controls required for an
official deployment. The separated paid topology is retained in
[`render.paid.yaml`](render.paid.yaml).

### Deployment, privacy, and audit boundary

The supplied Compose configuration is for local demonstration, acceptance
testing, and controlled evaluation. Before a shared or official deployment,
disable local single-user access, use unique secrets and an organizational
identity provider, terminate TLS at a trusted gateway, enforce network and
upload controls, replace all development credentials, and implement the
jurisdiction's retention, backup, and WORM/object-lock requirements.

Do not process images without lawful authority, a defined purpose, and an
appropriate data-protection basis. Synthetic fixtures in `demo_data/` prove
software flow only; they cannot validate the real-world performance of a model.
Fairness metrics are audit evidence, not stand-alone legal conclusions: sample
representativeness, label quality, thresholds, applicable law, and human review
remain essential.

### Copyright

Copyright © 2026 Rain Liu. All rights reserved. This is a proprietary project;
see [LICENSE](LICENSE) for usage restrictions.
