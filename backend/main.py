import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from api import api_router
from api import auth as auth_api
from core.config import settings
from core.database import AsyncSessionLocal, init_db
from core.i18n import bilingual
from services.audit_service import append_audit_log
from services.demo_service import seed_demo_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    if settings.local_single_user_mode:
        async with AsyncSessionLocal() as session:
            await auth_api.ensure_local_administrator(session)
    if settings.seed_demo_data:
        async with AsyncSessionLocal() as session:
            await seed_demo_data(session)
    yield


app = FastAPI(
    title="Fair Bench｜公允准鉴 API",
    summary="Public-sector facial recognition algorithm fairness audit platform",
    description=(
        "面向公共AI监管机构的标准化人脸算法公平性评测接口。"
        "All mutation responses include bilingual messages."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith(settings.api_prefix):
        # Every API access gets a generic trace event; mutation routes also append
        # richer domain events inside their own transaction.
        async with AsyncSessionLocal() as session:
            await append_audit_log(
                session,
                actor_id=getattr(request.state, "actor", None).actor_id
                if getattr(request.state, "actor", None)
                else "anonymous",
                actor_role=getattr(request.state, "actor", None).role
                if getattr(request.state, "actor", None)
                else "anonymous",
                action=f"api.{request.method.lower()}",
                resource_type="api_route",
                resource_id=request.url.path,
                request_id=request.state.request_id,
                ip_address=request.client.host if request.client else None,
                details={"status_code": response.status_code},
            )
            await session.commit()
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return ORJSONResponse(
        status_code=422,
        content={
            "message": bilingual("validation_error"),
            "errors": exc.errors(),
        },
    )


@app.get("/health", tags=["System"])
async def health() -> dict:
    return {
        "status": "ok",
        "service": "fairbench-api",
        "message": bilingual("ok"),
    }


app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(auth_api.router, prefix=settings.api_prefix)
