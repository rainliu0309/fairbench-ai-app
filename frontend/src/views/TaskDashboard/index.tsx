import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Download,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { downloadFile } from "../../api/client";
import { datasetApi, statsApi, taskApi } from "../../api/endpoints";
import type { EvaluationTask } from "../../api/types";
import { DataTable, type Column } from "../../components/common/DataTable";
import { PageHeader } from "../../components/common/PageHeader";
import { ProgressBar } from "../../components/common/ProgressBar";
import { StatusTag } from "../../components/common/StatusTag";
import { FailedSamplesDrawer } from "../../components/task/FailedSamplesDrawer";
import { TaskCreateModal } from "../../components/task/TaskCreateModal";
import { Modal } from "../../components/common/Modal";
import { isSeededDemoTask, taskDisplayName } from "../../utils/display";

export function TaskDashboard() {
  const { i18n, t } = useTranslation();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<EvaluationTask | null>(null);
  const [taskToDelete, setTaskToDelete] = useState<EvaluationTask | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const datasets = useQuery({
    queryKey: ["datasets", "task-selector"],
    queryFn: () => datasetApi.list("", 1),
  });
  const tasks = useQuery({
    queryKey: ["tasks"],
    queryFn: () => taskApi.list(),
    refetchInterval: (query) =>
      query.state.data?.items.some((item) =>
        ["queued", "running"].includes(item.status),
      )
        ? 2000
        : false,
  });
  const overview = useQuery({
    queryKey: ["stats-overview"],
    queryFn: statsApi.overview,
  });
  const failed = useQuery({
    queryKey: ["failed-samples", selectedTask?.id],
    queryFn: () => taskApi.failed(selectedTask!.id),
    enabled: Boolean(selectedTask),
  });
  const createTask = useMutation({
    mutationFn: taskApi.create,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["stats-overview"] }),
      ]);
      setCreateOpen(false);
    },
  });
  const retry = useMutation({
    mutationFn: (secret: string) => taskApi.retry(selectedTask!.id, secret),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
        queryClient.invalidateQueries({
          queryKey: ["failed-samples", selectedTask?.id],
        }),
      ]);
      setSelectedTask(null);
    },
  });
  const removeTask = useMutation({
    mutationFn: (taskId: string) => taskApi.remove(taskId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["stats-overview"] }),
        queryClient.invalidateQueries({ queryKey: ["reports"] }),
      ]);
      setTaskToDelete(null);
    },
  });

  const items = tasks.data?.items ?? [];
  const filteredItems = items.filter(
    (item) =>
      (!statusFilter || item.status === statusFilter) &&
      (!search ||
        taskDisplayName(item, t).toLowerCase().includes(search.toLowerCase()) ||
        item.algorithm_name.toLowerCase().includes(search.toLowerCase())),
  );
  const activeCount = items.filter((item) =>
    ["queued", "running"].includes(item.status),
  ).length;
  const riskCount = items.filter(
    (item) => item.metrics && !item.metrics.is_compliant,
  ).length;
  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(i18n.language.startsWith("en") ? "en-CA" : "zh-CN", {
        dateStyle: "medium",
        timeStyle: "short",
      }),
    [i18n.language],
  );
  const columns: Column<EvaluationTask>[] = [
    {
      key: "task",
      header: t("task.taskName"),
      render: (row) => (
        <div>
          <div className="primary-cell">{taskDisplayName(row, t)}</div>
          <div className="secondary-cell">{row.algorithm_name}</div>
        </div>
      ),
    },
    {
      key: "status",
      header: t("common.status"),
      render: (row) => <StatusTag status={row.status} />,
    },
    {
      key: "progress",
      header: t("task.progress"),
      render: (row) => (
        <div style={{ width: 130 }}>
          <ProgressBar value={row.progress} />
        </div>
      ),
    },
    {
      key: "compliance",
      header: t("task.compliance"),
      render: (row) =>
        row.metrics ? (
          <StatusTag status={row.metrics.is_compliant ? "compliant" : "warning"} />
        ) : (
          <span className="secondary-cell">{t("common.notAvailable")}</span>
        ),
    },
    {
      key: "created",
      header: t("task.createdAt"),
      render: (row) => dateFormatter.format(new Date(row.created_at)),
    },
    {
      key: "actions",
      header: t("common.actions"),
      render: (row) => (
        <div className="task-action-group">
          <button
            type="button"
            className="button ghost"
            onClick={() => downloadFile(`/tasks/${row.id}/results.csv`, `${row.id}-results.csv`)}
          >
            <Download />
            CSV
          </button>
          {row.status === "partial" || row.status === "failed" ? (
            <button
              type="button"
              className="button ghost"
              onClick={() => setSelectedTask(row)}
            >
              <RotateCcw />
              {t("task.viewFailures")}
            </button>
          ) : null}
          <span className="task-action-spacer" aria-hidden="true" />
          {!(["queued", "running"] as string[]).includes(row.status) && !isSeededDemoTask(row) ? (
            <button
              type="button"
              className="button ghost danger-action task-delete-button"
              onClick={() => setTaskToDelete(row)}
              aria-label={t("task.deleteTask")}
              title={t("task.deleteTask")}
            >
              <Trash2 />
            </button>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <div className="page">
      <PageHeader
        eyebrow={t("task.eyebrow")}
        title={t("task.title")}
        description={t("task.description")}
        action={
          <button type="button" className="button" onClick={() => setCreateOpen(true)}>
            <Plus />
            {t("task.newTask")}
          </button>
        }
      />
      <div className="summary-grid">
        <div className="stat-card">
          <div className="stat-card-head">
            <div className="stat-label">{t("task.activeTasks")}</div>
            <div className="stat-icon"><Activity /></div>
          </div>
          <div className="stat-value">{activeCount}</div>
          <div className="stat-meta">{t("task.polling")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-head">
            <div className="stat-label">{t("task.completedTasks")}</div>
            <div className="stat-icon"><CheckCircle2 /></div>
          </div>
          <div className="stat-value">{overview.data?.completed_count ?? 0}</div>
          <div className="stat-meta">
            {t("common.total", { total: overview.data?.task_count ?? 0 })}
          </div>
        </div>
        <div className="stat-card warning">
          <div className="stat-card-head">
            <div className="stat-label">{t("task.riskAlerts")}</div>
            <div className="stat-icon warning"><AlertTriangle /></div>
          </div>
          <div className="stat-value">{riskCount}</div>
          <div className="stat-meta">
            <AlertTriangle size={11} /> {t("status.warning")}
          </div>
        </div>
        <div className="stat-card warning">
          <div className="stat-card-head">
            <div className="stat-label">{t("task.failedSamples")}</div>
            <div className="stat-icon warning"><XCircle /></div>
          </div>
          <div className="stat-value">{overview.data?.failed_sample_count ?? 0}</div>
          <div className="stat-meta">{t("task.failedTitle")}</div>
        </div>
      </div>
      <div className="panel task-table-panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">{t("task.title")}</div>
            <div className="panel-subtitle">{t("task.polling")}</div>
          </div>
          <div className="toolbar-group">
            <div className="search-field">
              <Search />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("common.search")}
              />
            </div>
            <select
              className="language-select"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              aria-label={t("common.filter")}
            >
              <option value="">{t("common.all")}</option>
              {["queued", "running", "completed", "partial", "failed"].map(
                (status) => (
                  <option value={status} key={status}>
                    {t(`status.${status}`)}
                  </option>
                ),
              )}
            </select>
          </div>
        </div>
        <DataTable
          rows={filteredItems}
          columns={columns}
          rowKey={(row) => row.id}
          loading={tasks.isLoading}
        />
      </div>

      <TaskCreateModal
        open={createOpen}
        pending={createTask.isPending}
        datasets={datasets.data?.items ?? []}
        onClose={() => setCreateOpen(false)}
        onSubmit={(payload) => createTask.mutate(payload)}
      />
      <FailedSamplesDrawer
        task={selectedTask}
        samples={failed.data ?? []}
        loading={failed.isLoading}
        retrying={retry.isPending}
        onClose={() => setSelectedTask(null)}
        onRetry={(secret) => retry.mutate(secret)}
      />
      <Modal
        open={Boolean(taskToDelete)}
        title={t("task.deleteTitle")}
        onClose={() => !removeTask.isPending && setTaskToDelete(null)}
        footer={
          <>
            <button type="button" className="button secondary" disabled={removeTask.isPending} onClick={() => setTaskToDelete(null)}>
              {t("common.cancel")}
            </button>
            <button type="button" className="button danger" disabled={removeTask.isPending} onClick={() => taskToDelete && removeTask.mutate(taskToDelete.id)}>
              <Trash2 />
              {t("task.confirmDelete")}
            </button>
          </>
        }
      >
        <p className="delete-confirmation">
          {t("task.deleteWarning", { name: taskToDelete ? taskDisplayName(taskToDelete, t) : "" })}
        </p>
      </Modal>
    </div>
  );
}
