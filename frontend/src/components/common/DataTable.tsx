import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { EmptyState } from "./EmptyState";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  loading?: boolean;
  page?: number;
  total?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
}

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  loading = false,
  page = 1,
  total = rows.length,
  pageSize = 10,
  onPageChange,
}: DataTableProps<T>) {
  const { t } = useTranslation();
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  if (loading) return <div className="loading-row">{t("common.loading")}</div>;
  if (!rows.length) return <EmptyState />;

  return (
    <>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key}>{column.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((column) => (
                  <td
                    key={column.key}
                    data-label={
                      typeof column.header === "string" ? column.header : column.key
                    }
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {onPageChange ? (
        <div className="pagination">
          <span>{t("common.total", { total })}</span>
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            aria-label={t("common.previous")}
          >
            ‹
          </button>
          <span>{t("common.page", { page })}</span>
          <button
            type="button"
            disabled={page >= maxPage}
            onClick={() => onPageChange(page + 1)}
            aria-label={t("common.next")}
          >
            ›
          </button>
        </div>
      ) : null}
    </>
  );
}
