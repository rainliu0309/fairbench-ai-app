"""Conflict-free ARq CLI entry point.

The required ``backend/queue`` package is retained for task organization, while
the CLI imports this top-level module to avoid colliding with Python's standard
library module named ``queue``.
"""

from arq.connections import RedisSettings

from core.config import settings
from services.task_service import annotate_dataset, run_evaluation


class WorkerSettings:
    functions = [run_evaluation, annotate_dataset]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = settings.worker_max_jobs
    job_timeout = 60 * 60
    keep_result = 3600
