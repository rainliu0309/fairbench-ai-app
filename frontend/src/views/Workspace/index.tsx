import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Archive,
  ArrowRight,
  BarChart3,
  ClipboardCheck,
  Database,
  FileText,
  ListChecks,
} from "lucide-react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { datasetApi, reportApi, statsApi, taskApi } from "../../api/endpoints";
import type { EvaluationTask } from "../../api/types";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusTag } from "../../components/common/StatusTag";
import { taskDisplayName } from "../../utils/display";

type WorkflowStep = {
  number: string;
  path: string;
  icon: typeof Database;
  titleKey: string;
  descriptionKey: string;
  status: string;
};

function taskDate(task: EvaluationTask, locale: string) {
  return new Intl.DateTimeFormat(locale.startsWith("en") ? "en-CA" : "zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(task.completed_at ?? task.created_at));
}

export function Workspace() {
  const { i18n, t } = useTranslation();
  const datasets = useQuery({
    queryKey: ["datasets", "workspace"],
    queryFn: () => datasetApi.list("", 1),
  });
  const tasks = useQuery({
    queryKey: ["tasks", "workspace"],
    queryFn: () => taskApi.list(),
  });
  const reports = useQuery({
    queryKey: ["reports", "workspace"],
    queryFn: reportApi.list,
  });
  const overview = useQuery({
    queryKey: ["stats-overview", "workspace"],
    queryFn: statsApi.overview,
  });

  const taskItems = useMemo(() => tasks.data?.items ?? [], [tasks.data?.items]);
  const datasetItems = useMemo(
    () => datasets.data?.items ?? [],
    [datasets.data?.items],
  );
  const runningTasks = taskItems.filter((task) => ["queued", "running"].includes(task.status));
  const alertTasks = taskItems.filter((task) => task.metrics && !task.metrics.is_compliant);
  const labelReviewDatasets = datasetItems.filter((dataset) => dataset.status === "label_review_required");
  const recentTasks = useMemo(
    () => [...taskItems].sort((left, right) => right.created_at.localeCompare(left.created_at)).slice(0, 4),
    [taskItems],
  );

  const nextAction = labelReviewDatasets.length
    ? { path: "/datasets", title: t("workspace.actionLabelReview"), detail: t("workspace.actionLabelReviewDetail", { count: labelReviewDatasets.length }) }
    : runningTasks.length
      ? { path: "/tasks", title: t("workspace.actionTaskReview"), detail: t("workspace.actionTaskReviewDetail", { count: runningTasks.length }) }
      : alertTasks.length
        ? { path: "/dashboard", title: t("workspace.actionAlertReview"), detail: t("workspace.actionAlertReviewDetail", { count: alertTasks.length }) }
        : { path: "/datasets", title: t("workspace.actionStart"), detail: t("workspace.actionStartDetail") };

  const workflow: WorkflowStep[] = [
    {
      number: "01",
      path: "/datasets",
      icon: Database,
      titleKey: "workspace.datasetStepTitle",
      descriptionKey: "workspace.datasetStepDescription",
      status: t("workspace.datasetStepStatus", { count: overview.data?.dataset_count ?? 0 }),
    },
    {
      number: "02",
      path: "/tasks",
      icon: ClipboardCheck,
      titleKey: "workspace.taskStepTitle",
      descriptionKey: "workspace.taskStepDescription",
      status: t("workspace.taskStepStatus", { count: runningTasks.length }),
    },
    {
      number: "03",
      path: "/dashboard",
      icon: BarChart3,
      titleKey: "workspace.dashboardStepTitle",
      descriptionKey: "workspace.dashboardStepDescription",
      status: t("workspace.dashboardStepStatus", { count: alertTasks.length }),
    },
    {
      number: "04",
      path: "/reports",
      icon: FileText,
      titleKey: "workspace.reportStepTitle",
      descriptionKey: "workspace.reportStepDescription",
      status: t("workspace.reportStepStatus", { count: reports.data?.length ?? 0 }),
    },
  ];

  return (
    <div className="page workspace-page">
      <PageHeader
        eyebrow={t("workspace.eyebrow")}
        title={t("workspace.title")}
        description={t("workspace.description")}
        action={
          <Link className="button" to={nextAction.path}>
            {nextAction.title}
            <ArrowRight />
          </Link>
        }
      />

      <section className="workspace-section" aria-labelledby="workspace-overview-title">
        <div className="workspace-section-head">
          <div>
            <div className="section-kicker">{t("workspace.overviewKicker")}</div>
            <h2 id="workspace-overview-title">{t("workspace.overviewTitle")}</h2>
          </div>
        </div>
        <div className="summary-grid workspace-summary-grid">
          <div className="stat-card">
            <div className="stat-card-head"><span className="stat-label">{t("workspace.datasetCount")}</span><span className="stat-icon"><Database /></span></div>
            <div className="stat-value">{overview.data?.dataset_count ?? 0}</div>
            <div className="stat-meta">{t("workspace.datasetCountHint")}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-head"><span className="stat-label">{t("workspace.runningCount")}</span><span className="stat-icon"><ClipboardCheck /></span></div>
            <div className="stat-value">{runningTasks.length}</div>
            <div className="stat-meta">{t("workspace.runningCountHint")}</div>
          </div>
          <div className={`stat-card ${alertTasks.length ? "warning" : ""}`}>
            <div className="stat-card-head"><span className="stat-label">{t("workspace.alertCount")}</span><span className={`stat-icon ${alertTasks.length ? "warning" : ""}`}><AlertTriangle /></span></div>
            <div className="stat-value">{alertTasks.length}</div>
            <div className="stat-meta">{t("workspace.alertCountHint")}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-head"><span className="stat-label">{t("workspace.archiveCount")}</span><span className="stat-icon"><Archive /></span></div>
            <div className="stat-value">{reports.data?.length ?? 0}</div>
            <div className="stat-meta">{t("workspace.archiveCountHint", { rate: Math.round((overview.data?.compliance_rate ?? 0) * 100) })}</div>
          </div>
        </div>
      </section>

      <section className="workspace-section workspace-flow-section" aria-labelledby="workspace-flow-title">
        <div className="workspace-section-head">
          <div>
            <div className="section-kicker">{t("workspace.flowKicker")}</div>
            <h2 id="workspace-flow-title">{t("workspace.flowTitle")}</h2>
            <p>{t("workspace.flowDescription")}</p>
          </div>
        </div>
        <div className="workspace-flow">
          {workflow.map((step) => {
            const Icon = step.icon;
            return (
              <Link className="workflow-card" to={step.path} key={step.number}>
                <div className="workflow-card-top">
                  <span className="workflow-number">{step.number}</span>
                  <span className="workflow-icon"><Icon /></span>
                </div>
                <h3>{t(step.titleKey)}</h3>
                <p>{t(step.descriptionKey)}</p>
                <div className="workflow-status"><span className="state-dot" />{step.status}</div>
                <span className="workflow-link">{t("workspace.openStep")}<ArrowRight /></span>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="workspace-lower-grid">
        <div className="panel workspace-todo-panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">{t("workspace.todoKicker")}</div>
              <h2>{t("workspace.todoTitle")}</h2>
            </div>
            <ListChecks />
          </div>
          <div className="panel-body">
            <Link className="workspace-todo" to={nextAction.path}>
              <span className="workspace-todo-icon"><ArrowRight /></span>
              <span><strong>{nextAction.title}</strong><small>{nextAction.detail}</small></span>
            </Link>
          </div>
        </div>
        <div className="panel workspace-recent-panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">{t("workspace.recentKicker")}</div>
              <h2>{t("workspace.recentTitle")}</h2>
            </div>
            <Link className="button ghost workspace-panel-link" to="/tasks">{t("workspace.viewAllTasks")}<ArrowRight /></Link>
          </div>
          <div className="workspace-recent-list">
            {recentTasks.length ? recentTasks.map((task) => (
              <Link className="workspace-recent-row" to="/tasks" key={task.id}>
                <div className="workspace-recent-main"><strong>{taskDisplayName(task, t)}</strong><span>{task.algorithm_name}</span></div>
                <div className="workspace-recent-meta"><StatusTag status={task.status} /><time>{taskDate(task, i18n.language)}</time></div>
              </Link>
            )) : <div className="workspace-empty">{t("workspace.noRecentTasks")}</div>}
          </div>
        </div>
      </section>
    </div>
  );
}
