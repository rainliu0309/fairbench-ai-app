import { Check, FileCheck2, FileText, ListChecks } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { EvaluationTask } from "../../api/types";
import type { ReportPayload } from "../../api/endpoints";

interface ReportConfigFormProps {
  tasks: EvaluationTask[];
  value: ReportPayload;
  pending: boolean;
  onChange: (value: ReportPayload) => void;
  onGenerate: () => void;
}

export function ReportConfigForm({
  tasks,
  value,
  pending,
  onChange,
  onGenerate,
}: ReportConfigFormProps) {
  const { t } = useTranslation();
  const update = <K extends keyof ReportPayload>(
    key: K,
    next: ReportPayload[K],
  ) => onChange({ ...value, [key]: next });

  return (
    <section className="panel">
      <div className="panel-header">
        <div className="panel-title">{t("report.config")}</div>
      </div>
      <div className="panel-body">
        <div className="form-grid report-config-grid">
          <div className="form-field full">
            <label htmlFor="report-task">{t("report.task")}</label>
            <select
              id="report-task"
              value={value.task_id}
              onChange={(event) => update("task_id", event.target.value)}
            >
              {tasks.map((task) => (
                <option value={task.id} key={task.id}>
                  {task.algorithm_name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field full">
            <label htmlFor="report-title">{t("report.reportTitle")}</label>
            <input
              id="report-title"
              value={value.title}
              onChange={(event) => update("title", event.target.value)}
              placeholder={t("report.titlePlaceholder")}
            />
          </div>
          <div className="form-field full">
            <label htmlFor="report-language">{t("report.language")}</label>
            <select
              id="report-language"
              value={value.language}
              onChange={(event) => update("language", event.target.value)}
            >
              <option value="zh">{t("topbar.zh")}</option>
              <option value="en">{t("topbar.en")}</option>
            </select>
          </div>
          <div className="form-field full">
            <label htmlFor="report-authority">{t("report.authority")}</label>
            <input
              id="report-authority"
              value={value.issuing_authority}
              onChange={(event) => update("issuing_authority", event.target.value)}
              placeholder={t("report.authorityPlaceholder")}
            />
          </div>
          <div className="form-field full">
            <label htmlFor="report-signer">{t("report.signer")}</label>
            <input
              id="report-signer"
              value={value.signer}
              onChange={(event) => update("signer", event.target.value)}
              placeholder={t("report.signerPlaceholder")}
            />
          </div>
          <div className="report-options full">
            <div className="report-options-label">{t("report.contentScope")}</div>
            <button
              type="button"
              className={`report-option ${value.include_methodology ? "selected" : ""}`}
              aria-pressed={value.include_methodology}
              onClick={() => update("include_methodology", !value.include_methodology)}
            >
              <span className="report-option-icon"><FileText /></span>
              <span className="report-option-copy"><strong>{t("report.includeMethodology")}</strong><small>{t("report.methodologyOptionHint")}</small></span>
              <span className="option-check"><Check /></span>
            </button>
            <button
              type="button"
              className={`report-option ${value.include_failed_samples ? "selected" : ""}`}
              aria-pressed={value.include_failed_samples}
              onClick={() => update("include_failed_samples", !value.include_failed_samples)}
            >
              <span className="report-option-icon"><ListChecks /></span>
              <span className="report-option-copy"><strong>{t("report.includeFailures")}</strong><small>{t("report.failuresOptionHint")}</small></span>
              <span className="option-check"><Check /></span>
            </button>
          </div>
          <button
            type="button"
            className="button report-generate full"
            disabled={
              pending ||
              !value.task_id ||
              value.title.trim().length < 2 ||
              !value.issuing_authority ||
              !value.signer
            }
            onClick={onGenerate}
          >
            <FileCheck2 />
            {t("report.generate")}
          </button>
        </div>
      </div>
    </section>
  );
}
