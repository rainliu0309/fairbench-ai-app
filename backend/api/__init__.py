from fastapi import APIRouter, Depends

from api import audit, dataset, report, stats, task
from api.deps import get_actor

api_router = APIRouter(dependencies=[Depends(get_actor)])
api_router.include_router(dataset.router)
api_router.include_router(task.router)
api_router.include_router(stats.router)
api_router.include_router(report.router)
api_router.include_router(audit.router)
