import { Inbox } from "lucide-react";
import { useTranslation } from "react-i18next";

export function EmptyState({ message }: { message?: string }) {
  const { t } = useTranslation();
  return (
    <div className="empty-state">
      <div>
        <Inbox />
        {message ?? t("common.empty")}
      </div>
    </div>
  );
}
