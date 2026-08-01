import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FolderOpen, Plus, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { downloadFile } from "../../api/client";
import { datasetApi } from "../../api/endpoints";
import type { Dataset, Sample } from "../../api/types";
import { DataTable, type Column } from "../../components/common/DataTable";
import { Drawer } from "../../components/common/Drawer";
import { Modal } from "../../components/common/Modal";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusTag } from "../../components/common/StatusTag";
import { DatasetUploadModal } from "../../components/dataset/DatasetUploadModal";
import { SampleGrid } from "../../components/dataset/SampleGrid";
import { SampleLabelModal } from "../../components/dataset/SampleLabelModal";
import {
  datasetDisplayDescription,
  datasetDisplayName,
} from "../../utils/display";

export function DatasetManage() {
  const { i18n, t } = useTranslation();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [selectedSample, setSelectedSample] = useState<Sample | null>(null);
  const [datasetToDelete, setDatasetToDelete] = useState<Dataset | null>(null);

  const datasets = useQuery({
    queryKey: ["datasets", search, page],
    queryFn: () => datasetApi.list(search, page),
  });
  const samples = useQuery({
    queryKey: ["samples", selectedDataset?.id],
    queryFn: () => datasetApi.samples(selectedDataset!.id),
    enabled: Boolean(selectedDataset),
  });
  const upload = useMutation({
    mutationFn: (payload: { name: string; description: string; files: File[] }) =>
      datasetApi.upload(payload, setUploadProgress),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["datasets"] });
      setUploadOpen(false);
      setUploadProgress(0);
    },
  });
  const updateLabels = useMutation({
    mutationFn: (payload: Record<string, string>) =>
      datasetApi.updateLabels(
        selectedSample!.dataset_id,
        selectedSample!.id,
        payload,
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["samples", selectedDataset?.id],
      });
      setSelectedSample(null);
    },
  });
  const removeDataset = useMutation({
    mutationFn: (datasetId: string) => datasetApi.remove(datasetId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["datasets"] }),
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["reports"] }),
        queryClient.invalidateQueries({ queryKey: ["stats-overview"] }),
      ]);
      setDatasetToDelete(null);
      setSelectedDataset(null);
    },
  });

  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(i18n.language.startsWith("en") ? "en-CA" : "zh-CN", {
        dateStyle: "medium",
      }),
    [i18n.language],
  );

  const columns: Column<Dataset>[] = [
    {
      key: "name",
      header: t("dataset.datasetName"),
      render: (row) => (
        <div>
          <div className="primary-cell">{datasetDisplayName(row, t)}</div>
          <div className="secondary-cell">
            {datasetDisplayDescription(row, t)}
          </div>
        </div>
      ),
    },
    {
      key: "samples",
      header: t("dataset.sampleCount"),
      render: (row) => <span className="mono">{row.sample_count}</span>,
    },
    {
      key: "status",
      header: t("common.status"),
      render: (row) => <StatusTag status={row.status} />,
    },
    {
      key: "created",
      header: t("dataset.createdAt"),
      render: (row) => dateFormatter.format(new Date(row.created_at)),
    },
    {
      key: "actions",
      header: t("common.actions"),
      render: (row) => (
        <div className="dataset-action-group">
          <button
            type="button"
            className="button ghost dataset-open-button"
            onClick={() => setSelectedDataset(row)}
            aria-label={t("dataset.openDataset")}
            title={t("dataset.openDataset")}
          >
            <FolderOpen />
          </button>
          {!row.is_demo ? (
            <button
              type="button"
              className="button ghost danger-action task-delete-button"
              onClick={() => setDatasetToDelete(row)}
              aria-label={t("dataset.deleteDataset")}
              title={t("dataset.deleteDataset")}
            >
              <Trash2 />
            </button>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <div className="page">
      <PageHeader
        eyebrow={t("dataset.eyebrow")}
        title={t("dataset.title")}
        description={t("dataset.description")}
        action={
          <button type="button" className="button" onClick={() => setUploadOpen(true)}>
            <Plus />
            {t("dataset.newDataset")}
          </button>
        }
      />
      <div className="panel dataset-table-panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">{t("dataset.title")}</div>
            <div className="panel-subtitle">
              {t("common.total", { total: datasets.data?.total ?? 0 })}
            </div>
          </div>
          <div className="toolbar-group">
            <div className="search-field">
              <Search />
              <input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder={t("dataset.searchPlaceholder")}
              />
            </div>
          </div>
        </div>
        <DataTable
          rows={datasets.data?.items ?? []}
          columns={columns}
          rowKey={(row) => row.id}
          loading={datasets.isLoading}
          page={page}
          total={datasets.data?.total}
          pageSize={datasets.data?.page_size}
          onPageChange={setPage}
        />
      </div>

      <DatasetUploadModal
        open={uploadOpen}
        pending={upload.isPending}
        progress={uploadProgress}
        onClose={() => setUploadOpen(false)}
        onSubmit={(payload) => upload.mutate(payload)}
      />

      <Drawer
        open={Boolean(selectedDataset)}
        title={`${t("dataset.detailTitle")} · ${
          selectedDataset ? datasetDisplayName(selectedDataset, t) : ""
        }`}
        onClose={() => setSelectedDataset(null)}
      >
        <div className="toolbar">
          <div>
            <div className="panel-title">
              {selectedDataset
                ? datasetDisplayName(selectedDataset, t)
                : ""}
            </div>
            <div className="panel-subtitle">
              {t("dataset.sampleCount")} · {selectedDataset?.sample_count}
            </div>
          </div>
          {selectedDataset ? (
            <button
              type="button"
              className="button secondary"
              onClick={() => downloadFile(`/datasets/${selectedDataset.id}/export.csv`, `${selectedDataset.id}.csv`)}
            >
              <Download />
              {t("common.exportCsv")}
            </button>
          ) : null}
        </div>
        <SampleGrid
          samples={samples.data?.items ?? []}
          loading={samples.isLoading}
          onEdit={setSelectedSample}
        />
      </Drawer>

      <SampleLabelModal
        sample={selectedSample}
        pending={updateLabels.isPending}
        onClose={() => setSelectedSample(null)}
        onSave={(payload) => updateLabels.mutate(payload)}
      />
      <Modal
        open={Boolean(datasetToDelete)}
        title={t("dataset.deleteTitle")}
        onClose={() => !removeDataset.isPending && setDatasetToDelete(null)}
        footer={
          <>
            <button type="button" className="button secondary" disabled={removeDataset.isPending} onClick={() => setDatasetToDelete(null)}>
              {t("common.cancel")}
            </button>
            <button type="button" className="button danger" disabled={removeDataset.isPending} onClick={() => datasetToDelete && removeDataset.mutate(datasetToDelete.id)}>
              <Trash2 />
              {t("dataset.confirmDelete")}
            </button>
          </>
        }
      >
        <p className="delete-confirmation">
          {t("dataset.deleteWarning", { name: datasetToDelete ? datasetDisplayName(datasetToDelete, t) : "" })}
        </p>
      </Modal>
    </div>
  );
}
