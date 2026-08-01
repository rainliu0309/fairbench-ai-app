import { useTranslation } from "react-i18next";
import type { ReportPayload } from "../../api/endpoints";
import type { EvaluationTask, FailedSample } from "../../api/types";

interface ReportPreviewProps {
  config: ReportPayload;
  task: EvaluationTask | undefined;
  failedSamples: FailedSample[];
  failuresLoading: boolean;
}

export function ReportPreview({
  config,
  task,
  failedSamples,
  failuresLoading,
}: ReportPreviewProps) {
  const { i18n } = useTranslation();
  const t = i18n.getFixedT(config.language);
  const metrics = task?.metrics;
  const percent = (value?: number) => `${((value ?? 0) * 100).toFixed(1)}%`;

  return (
    <section className="panel">
      <div className="panel-header">
        <div className="panel-title">{t("report.preview")}</div>
      </div>
      <div className="report-paper-wrap">
        <article className="report-paper">
          <div className="paper-rule" />
          <div className="paper-classification">
            {t("report.official")} · {t("report.classification")}
          </div>
          <h2>{config.title || t("report.titlePlaceholder")}</h2>
          <div className="paper-meta">
            <div className="label">{t("report.reportNo")}</div>
            <div>FB-PREVIEW-2026</div>
            <div className="label">{t("report.authority")}</div>
            <div>{config.issuing_authority}</div>
            <div className="label">{t("task.algorithm")}</div>
            <div>{task?.algorithm_name ?? t("common.notAvailable")}</div>
            <div className="label">{t("task.threshold")}</div>
            <div>{percent(task?.fairness_threshold)}</div>
          </div>
          <div className="paper-section-title">{t("report.conclusion")}</div>
          <div className={`paper-verdict ${metrics?.is_compliant ? "" : "warning"}`}>
            {t(metrics?.is_compliant ? "report.pass" : "report.warn")}
          </div>
          <div className="paper-section-title">{t("report.metrics")}</div>
          <div className="paper-metrics">
            <div className="paper-metric">
              <div className="paper-metric-label">
                {t("dashboard.overallAccuracy")}
              </div>
              <div className="paper-metric-value">
                {percent(metrics?.overall_accuracy)}
              </div>
            </div>
            <div className="paper-metric">
              <div className="paper-metric-label">{t("dashboard.maxGap")}</div>
              <div className="paper-metric-value">
                {percent(metrics?.max_group_gap)}
              </div>
            </div>
            <div className="paper-metric">
              <div className="paper-metric-label">
                {t("dashboard.biasCoefficient")}
              </div>
              <div className="paper-metric-value">
                {(metrics?.bias_coefficient ?? 0).toFixed(3)}
              </div>
            </div>
            <div className="paper-metric">
              <div className="paper-metric-label">
                {t("dashboard.stdDeviation")}
              </div>
              <div className="paper-metric-value">
                {(metrics?.std_deviation ?? 0).toFixed(3)}
              </div>
            </div>
          </div>
          {config.include_methodology ? (
            <>
              <div className="paper-section-title">{t("report.methodology")}</div>
              <div className="paper-note">{t("report.methodologyText")}</div>
            </>
          ) : null}
          {config.include_failed_samples ? (
            <>
              <div className="paper-section-title">
                {t("report.failedSampleSummary")}
              </div>
              <div className="paper-failure-summary">
                <div className="paper-failure-total">
                  {failuresLoading
                    ? t("common.loading")
                    : t("report.failedSampleCount", {
                        count: failedSamples.length,
                      })}
                </div>
                {!failuresLoading && failedSamples.length ? (
                  <div className="paper-failure-list">
                    {failedSamples.slice(0, 3).map((sample) => (
                      <div className="paper-failure-row" key={sample.id}>
                        <span>{sample.error_code ?? t("common.notAvailable")}</span>
                        <span>
                          {sample.error_message ?? t("common.notAvailable")}
                        </span>
                      </div>
                    ))}
                    {failedSamples.length > 3 ? (
                      <div className="paper-failure-more">
                        {t("report.additionalFailureCount", {
                          count: failedSamples.length - 3,
                        })}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </>
          ) : null}
          <div className="paper-signature">
            {t("report.signature")} · {config.signer}
          </div>
          <div className="paper-draft">{t("report.draft")}</div>
        </article>
      </div>
    </section>
  );
}
