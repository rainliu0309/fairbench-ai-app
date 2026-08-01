import { RotateCcw } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { EvaluationTask, FailedSample } from "../../api/types";
import { DataTable, type Column } from "../common/DataTable";
import { Drawer } from "../common/Drawer";
import { StatusTag } from "../common/StatusTag";

interface FailedSamplesDrawerProps {
  task: EvaluationTask | null;
  samples: FailedSample[];
  loading: boolean;
  retrying: boolean;
  onClose: () => void;
  onRetry: (secret: string) => void;
}

export function FailedSamplesDrawer({
  task,
  samples,
  loading,
  retrying,
  onClose,
  onRetry,
}: FailedSamplesDrawerProps) {
  const { t } = useTranslation();
  const [secret, setSecret] = useState("");
  const columns: Column<FailedSample>[] = [
    {
      key: "sample",
      header: t("dataset.samplePreview"),
      render: (row) => <span className="mono">{row.sample_id.slice(0, 12)}…</span>,
    },
    {
      key: "status",
      header: t("common.status"),
      render: (row) => <StatusTag status={row.status} />,
    },
    {
      key: "code",
      header: t("task.errorCode"),
      render: (row) => <span className="mono">{row.error_code ?? "—"}</span>,
    },
    {
      key: "retries",
      header: t("task.retryCount"),
      render: (row) => row.retry_count,
    },
  ];

  return (
    <Drawer
      open={Boolean(task)}
      title={`${t("task.failedTitle")} · ${task?.algorithm_name ?? ""}`}
      onClose={onClose}
    >
      <DataTable
        rows={samples}
        columns={columns}
        rowKey={(row) => row.id}
        loading={loading}
      />
      <div className="panel" style={{ marginTop: 16 }}>
        <div className="panel-header">
          <div className="panel-title">{t("task.retryAll")}</div>
        </div>
        <div className="panel-body">
          <div className="form-field">
            <label htmlFor="retry-secret">{t("task.retrySecret")}</label>
            <input
              id="retry-secret"
              type="password"
              autoComplete="off"
              value={secret}
              onChange={(event) => setSecret(event.target.value)}
            />
            <span className="field-hint">{t("task.secretPolicy")}</span>
          </div>
          <button
            type="button"
            className="button danger"
            style={{ marginTop: 12 }}
            disabled={!samples.length || retrying}
            onClick={() => onRetry(secret)}
          >
            <RotateCcw />
            {t("task.retryAll")}
          </button>
        </div>
      </div>
    </Drawer>
  );
}
