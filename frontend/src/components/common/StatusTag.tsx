import { useTranslation } from "react-i18next";

const statusTone: Record<string, string> = {
  ready: "success",
  completed: "success",
  compliant: "success",
  running: "",
  processing: "",
  annotating: "",
  label_review_required: "warning",
  queued: "",
  pending: "",
  partial: "warning",
  warning: "danger",
  failed: "danger",
};

export function StatusTag({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <span className={`status-tag ${statusTone[status] ?? ""}`}>
      {t(`status.${status}`, { defaultValue: status })}
    </span>
  );
}
