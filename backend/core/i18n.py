from typing import Literal

Language = Literal["zh", "en"]

MESSAGES: dict[str, dict[Language, str]] = {
    "ok": {"zh": "操作成功", "en": "Operation completed successfully"},
    "created": {"zh": "创建成功", "en": "Created successfully"},
    "dataset_uploaded": {
        "zh": "测试图集已创建并开始处理",
        "en": "Dataset created and processing started",
    },
    "label_updated": {
        "zh": "人工修正标签已保存",
        "en": "Manual label correction saved",
    },
    "task_queued": {
        "zh": "评测任务已进入异步队列",
        "en": "Evaluation task queued",
    },
    "task_deleted": {
        "zh": "评测任务及其结果已删除，操作留痕已归档",
        "en": "Evaluation task and its results were deleted; the audit record remains archived",
    },
    "dataset_deleted": {
        "zh": "测试图集及其关联文件已删除，操作留痕已归档",
        "en": "Dataset and its related files were deleted; the audit record remains archived",
    },
    "demo_dataset_protected": {
        "zh": "公共演示图集受保护，不能删除",
        "en": "The public demo dataset is protected and cannot be deleted",
    },
    "dataset_active": {
        "zh": "图集正在处理或标注中，暂不能删除",
        "en": "A dataset cannot be deleted while it is processing or being annotated",
    },
    "task_active": {
        "zh": "正在排队或执行中的任务不能删除，请等待任务结束",
        "en": "Queued or running tasks cannot be deleted; wait for the task to finish",
    },
    "demo_task_protected": {
        "zh": "系统预置演示评测记录不可删除",
        "en": "System-provided demo evaluation records cannot be deleted",
    },
    "retry_queued": {
        "zh": "失败样本已重新进入队列",
        "en": "Failed samples requeued",
    },
    "report_ready": {
        "zh": "审计报告已生成",
        "en": "Audit report generated",
    },
    "not_found": {"zh": "未找到请求的资源", "en": "Requested resource not found"},
    "validation_error": {
        "zh": "请求参数校验失败",
        "en": "Request validation failed",
    },
    "secret_expired": {
        "zh": "接口密钥已过期，请重新提交",
        "en": "API secret expired; submit it again",
    },
    "dataset_not_ready": {
        "zh": "图集仍在标注或等待人工复核，暂不能发起评测",
        "en": "Dataset annotation is incomplete; finish review before starting an evaluation",
    },
    "auth_required": {
        "zh": "需要有效的登录会话，请重新登录",
        "en": "A valid signed-in session is required",
    },
    "invalid_credentials": {
        "zh": "账号或密码不正确",
        "en": "Email or password is incorrect",
    },
    "setup_completed": {
        "zh": "系统初始管理员已创建",
        "en": "Initial system administrator created",
    },
}


def bilingual(key: str) -> dict[str, str]:
    return MESSAGES.get(key, MESSAGES["ok"])
