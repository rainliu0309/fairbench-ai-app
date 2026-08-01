import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "../common/Modal";
import { ProgressBar } from "../common/ProgressBar";
import { UploadZone } from "../common/UploadZone";

interface DatasetUploadModalProps {
  open: boolean;
  pending: boolean;
  progress: number;
  onClose: () => void;
  onSubmit: (payload: {
    name: string;
    description: string;
    files: File[];
  }) => void;
}

export function DatasetUploadModal({
  open,
  pending,
  progress,
  onClose,
  onSubmit,
}: DatasetUploadModalProps) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);

  const valid = name.trim().length >= 2 && files.length > 0;
  const close = () => {
    if (pending) return;
    setName("");
    setDescription("");
    setFiles([]);
    onClose();
  };

  return (
    <Modal
      open={open}
      title={t("dataset.uploadTitle")}
      onClose={close}
      footer={
        <>
          <button type="button" className="button secondary" onClick={close}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="button"
            disabled={!valid || pending}
            onClick={() => onSubmit({ name, description, files })}
          >
            {t("dataset.uploadAction")}
          </button>
        </>
      }
    >
      <div className="form-grid">
        <div className="form-field full">
          <label htmlFor="dataset-name">{t("dataset.datasetName")}</label>
          <input
            id="dataset-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={t("dataset.namePlaceholder")}
            maxLength={160}
          />
        </div>
        <div className="form-field full">
          <label htmlFor="dataset-description">
            {t("dataset.descriptionLabel")}
          </label>
          <textarea
            id="dataset-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={t("dataset.descPlaceholder")}
            maxLength={2000}
          />
        </div>
        <div className="form-field full">
          <UploadZone files={files} onFiles={setFiles} />
        </div>
        {pending ? (
          <div className="form-field full">
            <label>{t("dataset.uploadProgress")}</label>
            <ProgressBar value={progress} />
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
