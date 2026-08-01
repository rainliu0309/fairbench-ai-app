import { ImageOff, Pencil, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { datasetApi } from "../../api/endpoints";
import type { Sample } from "../../api/types";
import { EmptyState } from "../common/EmptyState";

interface SampleGridProps {
  samples: Sample[];
  loading: boolean;
  onEdit: (sample: Sample) => void;
}

export function SampleGrid({ samples, loading, onEdit }: SampleGridProps) {
  const { t } = useTranslation();
  if (loading) return <div className="loading-row">{t("common.loading")}</div>;
  if (!samples.length) return <EmptyState />;

  return (
    <div className="sample-grid">
      {samples.map((sample, index) => (
        <SampleCard key={sample.id} sample={sample} index={index} onEdit={onEdit} />
      ))}
    </div>
  );
}

function SampleCard({
  sample,
  index,
  onEdit,
}: {
  sample: Sample;
  index: number;
  onEdit: (sample: Sample) => void;
}) {
  const { t } = useTranslation();
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    if (!sample.preview_url) return;
    let active = true;
    let url: string | null = null;
    datasetApi
      .imageBlob(sample.preview_url)
      .then((blob) => {
        url = URL.createObjectURL(blob);
        if (active) setImageUrl(url);
      })
      .catch(() => active && setImageFailed(true));
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [sample.preview_url]);

  const labels = sample.effective_labels;
  return (
    <article className="sample-card">
      <div className="sample-visual">
        <span className="sample-index">#{String(index + 1).padStart(2, "0")}</span>
        {imageUrl && !imageFailed ? (
          <img
            src={imageUrl}
            alt={t("dataset.samplePreview")}
            className="sample-image"
            onError={() => setImageFailed(true)}
          />
        ) : imageFailed ? (
          <ImageOff className="sample-face-icon" aria-label={t("dataset.previewUnavailable")} />
        ) : (
          <UserRound className="sample-face-icon" aria-label={t("dataset.samplePreview")} />
        )}
      </div>
      <div className="sample-content">
        <div className="sample-name" title={sample.filename}>{sample.filename}</div>
        <div className="label-list">
          {labels
            ? [labels.age_group, labels.gender, labels.ethnicity].map((label) => (
                <span className="label-chip" key={label}>
                  {t(`labels.${label}`, { defaultValue: label })}
                </span>
              ))
            : t("common.notAvailable")}
        </div>
        {sample.annotation_error && sample.label_source !== "manual" ? (
          <div className="sample-error">{t("dataset.annotationFailed")}</div>
        ) : null}
        <div className="sample-actions">
          <button
            type="button"
            className="button ghost sample-edit-button"
            onClick={() => onEdit(sample)}
            aria-label={t("common.edit")}
            title={t("common.edit")}
          >
            <Pencil />
          </button>
        </div>
      </div>
    </article>
  );
}
