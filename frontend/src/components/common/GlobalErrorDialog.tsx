import axios from "axios";
import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "./Modal";

export function GlobalErrorDialog() {
  const { i18n, t } = useTranslation();
  const [message, setMessage] = useState("");

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<unknown>).detail;
      if (axios.isAxiosError(detail)) {
        const payload = detail.response?.data as
          | { detail?: { zh?: string; en?: string }; message?: { zh?: string; en?: string } }
          | undefined;
        const bilingual = payload?.detail ?? payload?.message;
        const language = i18n.language.startsWith("en") ? "en" : "zh";
        setMessage(
          bilingual?.[language] ??
            detail.message ??
            t("common.errorDefault"),
        );
      } else {
        setMessage(t("common.errorDefault"));
      }
    };
    window.addEventListener("fairbench:api-error", handler);
    return () => window.removeEventListener("fairbench:api-error", handler);
  }, [i18n.language, t]);

  return (
    <Modal
      open={Boolean(message)}
      title={t("common.errorTitle")}
      onClose={() => setMessage("")}
      footer={
        <button type="button" className="button" onClick={() => setMessage("")}>
          {t("common.confirm")}
        </button>
      }
    >
      <div className="error-dialog-icon">
        <AlertTriangle />
      </div>
      <div className="error-message">{message}</div>
    </Modal>
  );
}
