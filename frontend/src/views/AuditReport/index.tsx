import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { downloadFile } from "../../api/client";
import { reportApi, type ReportPayload, taskApi } from "../../api/endpoints";
import type { ReportRecord } from "../../api/types";
import { DataTable, type Column } from "../../components/common/DataTable";
import { PageHeader } from "../../components/common/PageHeader";
import { ReportConfigForm } from "../../components/report/ReportConfigForm";
import { ReportPreview } from "../../components/report/ReportPreview";

export function AuditReport() {
  const { i18n, t } = useTranslation();
  const queryClient = useQueryClient();
  const tasks = useQuery({
    queryKey: ["tasks", "report"],
    queryFn: () => taskApi.list(),
  });
  const reports = useQuery({
    queryKey: ["reports"],
    queryFn: reportApi.list,
  });
  const eligibleTasks = useMemo(
    () => (tasks.data?.items ?? []).filter((task) => Boolean(task.metrics)),
    [tasks.data],
  );
  const [config, setConfig] = useState<ReportPayload>({
    task_id: "",
    language: i18n.language.startsWith("en") ? "en" : "zh",
    title: t("report.titlePlaceholder"),
    include_failed_samples: true,
    include_methodology: true,
    issuing_authority: t("report.authorityPlaceholder"),
    signer: t("report.signerPlaceholder"),
  });

  useEffect(() => {
    if (!config.task_id && eligibleTasks.length) {
      setConfig((current) => ({ ...current, task_id: eligibleTasks[0].id }));
    }
  }, [config.task_id, eligibleTasks]);

  const createReport = useMutation({
    mutationFn: reportApi.create,
    onSuccess: async (report) => {
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
      await downloadFile(`/reports/${report.id}/download`, `${report.report_no}.pdf`);
    },
  });
  const selectedTask = eligibleTasks.find((task) => task.id === config.task_id);
  const previewFailures = useQuery({
    queryKey: ["failed-samples", "report-preview", config.task_id],
    queryFn: () => taskApi.failed(config.task_id),
    enabled: Boolean(config.include_failed_samples && config.task_id),
  });
  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(i18n.language.startsWith("en") ? "en-CA" : "zh-CN", {
        dateStyle: "medium",
        timeStyle: "short",
      }),
    [i18n.language],
  );
  const columns: Column<ReportRecord>[] = [
    {
      key: "title",
      header: t("report.reportTitle"),
      render: (row) => (
        <div>
          <div className="primary-cell">{row.title}</div>
          <div className="secondary-cell mono">{row.report_no}</div>
        </div>
      ),
    },
    {
      key: "language",
      header: t("report.language"),
      render: (row) => (row.language === "zh" ? t("topbar.zh") : t("topbar.en")),
    },
    {
      key: "checksum",
      header: t("report.checksum"),
      render: (row) => (
        <span className="mono" title={row.checksum}>
          {row.checksum.slice(0, 14)}…
        </span>
      ),
    },
    {
      key: "created",
      header: t("report.generatedAt"),
      render: (row) => dateFormatter.format(new Date(row.created_at)),
    },
    {
      key: "actions",
      header: t("common.actions"),
      render: (row) => (
        <button type="button" className="button ghost" onClick={() => downloadFile(`/reports/${row.id}/download`, `${row.report_no}.pdf`)}>
          <Download />
          {t("report.downloadPdf")}
        </button>
      ),
    },
  ];

  return (
    <div className="page report-page">
      <PageHeader
        eyebrow={t("report.eyebrow")}
        title={t("report.title")}
        description={t("report.description")}
      />
      <div className="report-layout">
        <ReportConfigForm
          tasks={eligibleTasks}
          value={config}
          pending={createReport.isPending}
          onChange={setConfig}
          onGenerate={() => createReport.mutate(config)}
        />
        <ReportPreview
          config={config}
          task={selectedTask}
          failedSamples={previewFailures.data ?? []}
          failuresLoading={previewFailures.isLoading}
        />
      </div>
      <div className="panel report-history">
        <div className="panel-header">
          <div>
            <div className="panel-title">{t("report.history")}</div>
            <div className="panel-subtitle">
              {t("common.total", { total: reports.data?.length ?? 0 })}
            </div>
          </div>
        </div>
        <DataTable
          rows={reports.data ?? []}
          columns={columns}
          rowKey={(row) => row.id}
          loading={reports.isLoading}
        />
      </div>
    </div>
  );
}
