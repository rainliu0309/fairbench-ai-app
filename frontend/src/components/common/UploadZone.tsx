import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

interface UploadZoneProps {
  files: File[];
  onFiles: (files: File[]) => void;
}

export function UploadZone({ files, onFiles }: UploadZoneProps) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const acceptFiles = (items: FileList | null) => {
    if (!items) return;
    onFiles(
      Array.from(items).filter((file) =>
        ["image/jpeg", "image/png", "image/webp"].includes(file.type),
      ),
    );
  };

  return (
    <div
      className={`upload-zone ${dragging ? "dragging" : ""}`}
      onDragEnter={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        acceptFiles(event.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
      }}
      role="button"
      tabIndex={0}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        onChange={(event) => acceptFiles(event.target.files)}
      />
      <div>
        <div className="upload-icon">
          <UploadCloud />
        </div>
        <div className="upload-main">
          {files.length
            ? t("dataset.selectedFiles", { count: files.length })
            : t("dataset.uploadHint")}
        </div>
        <div className="upload-sub">{t("dataset.uploadLimit")}</div>
      </div>
    </div>
  );
}
