import { Activity, Scale, Sigma, Target } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Metrics } from "../../api/types";

interface MetricCardsProps {
  metrics: Metrics | null;
}

export function MetricCards({ metrics }: MetricCardsProps) {
  const { t } = useTranslation();
  const percent = (value: number | undefined) =>
    `${((value ?? 0) * 100).toFixed(1)}%`;

  return (
    <div className="summary-grid">
      <div className="stat-card">
        <div className="stat-card-head">
          <div className="stat-label">{t("dashboard.overallAccuracy")}</div>
          <div className="stat-icon"><Target /></div>
        </div>
        <div className="stat-value">{percent(metrics?.overall_accuracy)}</div>
        <div className="stat-meta">
          {t("dashboard.evaluatedSamples")} · {metrics?.evaluated_samples ?? 0}
        </div>
      </div>
      <div
        className={`stat-card ${
          metrics && metrics.max_group_gap > metrics.threshold ? "warning" : ""
        }`}
      >
        <div className="stat-card-head">
          <div className="stat-label">{t("dashboard.maxGap")}</div>
          <div className="stat-icon"><Scale /></div>
        </div>
        <div className="stat-value">{percent(metrics?.max_group_gap)}</div>
        <div className="stat-meta">
          {t("dashboard.threshold")} · {percent(metrics?.threshold)}
        </div>
      </div>
      <div className="stat-card">
        <div className="stat-card-head">
          <div className="stat-label">{t("dashboard.biasCoefficient")}</div>
          <div className="stat-icon"><Activity /></div>
        </div>
        <div className="stat-value">
          {(metrics?.bias_coefficient ?? 0).toFixed(3)}
        </div>
        <div className="stat-meta">{t("dashboard.auditFinding")}</div>
      </div>
      <div className="stat-card">
        <div className="stat-card-head">
          <div className="stat-label">{t("dashboard.stdDeviation")}</div>
          <div className="stat-icon"><Sigma /></div>
        </div>
        <div className="stat-value">
          {(metrics?.std_deviation ?? 0).toFixed(3)}
        </div>
        <div className="stat-meta">{t("dashboard.groupAccuracy")}</div>
      </div>
    </div>
  );
}
