import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Scale,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { datasetApi, statsApi, taskApi } from "../../api/endpoints";
import { EmptyState } from "../../components/common/EmptyState";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusTag } from "../../components/common/StatusTag";
import { FairnessCharts } from "../../components/dashboard/FairnessCharts";
import { MetricCards } from "../../components/dashboard/MetricCards";
import { datasetDisplayName } from "../../utils/display";

export function FairnessDashboard() {
  const { t } = useTranslation();
  const [datasetId, setDatasetId] = useState("");
  const [taskId, setTaskId] = useState("");
  const datasets = useQuery({
    queryKey: ["datasets", "dashboard-selector"],
    queryFn: () => datasetApi.list("", 1),
  });
  const tasks = useQuery({
    queryKey: ["tasks", "dashboard"],
    queryFn: () => taskApi.list(),
  });
  const compare = useQuery({
    queryKey: ["stats-compare", datasetId],
    queryFn: () => statsApi.compare(datasetId),
    enabled: Boolean(datasetId),
  });

  useEffect(() => {
    if (!datasetId && datasets.data?.items.length) {
      setDatasetId(datasets.data.items[0].id);
    }
  }, [datasetId, datasets.data]);

  const eligibleTasks = useMemo(
    () =>
      (tasks.data?.items ?? []).filter(
        (task) => task.dataset_id === datasetId && Boolean(task.metrics),
      ),
    [datasetId, tasks.data],
  );

  useEffect(() => {
    if (!eligibleTasks.length) {
      setTaskId("");
      return;
    }
    if (!eligibleTasks.some((task) => task.id === taskId)) {
      setTaskId(eligibleTasks[0].id);
    }
  }, [eligibleTasks, taskId]);

  const task = eligibleTasks.find((item) => item.id === taskId);
  const metrics = task?.metrics ?? null;
  const selectedDataset = datasets.data?.items.find(
    (item) => item.id === datasetId,
  );

  return (
    <div className="page">
      <PageHeader
        eyebrow={t("dashboard.eyebrow")}
        title={t("dashboard.title")}
        description={t("dashboard.description")}
        action={
          metrics ? (
            <StatusTag status={metrics.is_compliant ? "compliant" : "warning"} />
          ) : undefined
        }
      />
      <section className="oversight-strip">
        <div className="oversight-lead">
          <div className="oversight-symbol">
            <ShieldCheck />
          </div>
          <div>
            <div className="oversight-label">{t("dashboard.currentCycle")}</div>
            <div className="oversight-cycle">{t("dashboard.cycleValue")}</div>
            <div className="oversight-record">
              <span className="state-dot" />
              {t("dashboard.recordStatus")}
            </div>
          </div>
        </div>
        <div className="oversight-facts">
          <div className="oversight-fact">
            <Database />
            <div>
              <span>{t("dashboard.sampleScope")}</span>
              <strong>{selectedDataset?.sample_count ?? 0}</strong>
            </div>
          </div>
          <div className="oversight-fact algorithm">
            <ShieldCheck />
            <div>
              <span>{t("dashboard.selectedAlgorithm")}</span>
              <strong>{task?.algorithm_name ?? t("common.notAvailable")}</strong>
            </div>
          </div>
          <div className="oversight-fact policy">
            <Scale />
            <div>
              <span>{t("dashboard.policyBasis")}</span>
              <strong>{t("dashboard.policyValue")}</strong>
            </div>
          </div>
        </div>
      </section>
      <div className="panel filter-panel">
        <div className="panel-body">
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="dashboard-dataset">{t("dashboard.dataset")}</label>
              <select
                id="dashboard-dataset"
                value={datasetId}
                onChange={(event) => setDatasetId(event.target.value)}
              >
                {(datasets.data?.items ?? []).map((dataset) => (
                  <option value={dataset.id} key={dataset.id}>
                    {datasetDisplayName(dataset, t)}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="dashboard-task">{t("dashboard.primaryTask")}</label>
              <select
                id="dashboard-task"
                value={taskId}
                onChange={(event) => setTaskId(event.target.value)}
              >
                {eligibleTasks.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.algorithm_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>
      {metrics ? (
        <>
          <MetricCards metrics={metrics} />
          <FairnessCharts
            metrics={metrics}
            comparison={compare.data?.series ?? []}
          />
          <div className={`finding ${metrics.is_compliant ? "" : "warning"}`}>
            {metrics.is_compliant ? <CheckCircle2 /> : <AlertTriangle />}
            <div>
              <strong>{t("dashboard.auditFinding")}</strong>
              <br />
              {t(
                metrics.is_compliant
                  ? "dashboard.findingPass"
                  : "dashboard.findingWarn",
              )}
            </div>
          </div>
        </>
      ) : (
        <div className="panel">
          <EmptyState message={t("dashboard.noMetrics")} />
        </div>
      )}
    </div>
  );
}
