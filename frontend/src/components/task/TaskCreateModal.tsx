import { Info, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Dataset } from "../../api/types";
import { datasetDisplayName } from "../../utils/display";
import { Modal } from "../common/Modal";

interface TaskCreateModalProps {
  open: boolean;
  pending: boolean;
  datasets: Dataset[];
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}

export function TaskCreateModal({
  open,
  pending,
  datasets,
  onClose,
  onSubmit,
}: TaskCreateModalProps) {
  const { i18n, t } = useTranslation();
  const [datasetId, setDatasetId] = useState("");
  const [name, setName] = useState("");
  const [algorithm, setAlgorithm] = useState("");
  const [endpoint, setEndpoint] = useState(
    import.meta.env.VITE_SIMULATOR_URL ?? "http://simulator:8080/v1/face/recognize",
  );
  const [method, setMethod] = useState("POST");
  const [apiKey, setApiKey] = useState("");
  const [authScheme, setAuthScheme] = useState("none");
  const [authHeader, setAuthHeader] = useState("Authorization");
  const [imageField, setImageField] = useState("image");
  const [identityField, setIdentityField] = useState("expected_identity");
  const [identityPath, setIdentityPath] = useState("predicted_identity");
  const [confidencePath, setConfidencePath] = useState("confidence");
  const [correctPath, setCorrectPath] = useState("is_correct");
  const [extraFields, setExtraFields] = useState("{}");
  const [staticHeaders, setStaticHeaders] = useState("{}");
  const [showMapping, setShowMapping] = useState(false);
  const [threshold, setThreshold] = useState("0.10");
  const [language, setLanguage] = useState(
    i18n.language.startsWith("en") ? "en" : "zh",
  );

  useEffect(() => {
    if (!datasetId && datasets.length) setDatasetId(datasets[0].id);
  }, [datasetId, datasets]);

  const parsedExtraFields = useMemo(() => parseStringMap(extraFields), [extraFields]);
  const parsedStaticHeaders = useMemo(() => parseStringMap(staticHeaders), [staticHeaders]);

  const valid =
    Boolean(datasetId) &&
    name.trim().length >= 2 &&
    algorithm.trim().length >= 2 &&
    endpoint.trim().length >= 3 &&
    (authScheme === "none" || apiKey.trim().length > 0) &&
    parsedExtraFields.valid &&
    parsedStaticHeaders.valid &&
    Number(threshold) >= 0 &&
    Number(threshold) <= 1;

  return (
    <Modal
      open={open}
      title={t("task.newTask")}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="button"
            disabled={!valid || pending}
            onClick={() =>
              onSubmit({
                dataset_id: datasetId,
                name,
                algorithm_name: algorithm,
                target_api_url: endpoint,
                target_api_method: method,
                api_key: apiKey,
                provider_config: {
                  auth_scheme: authScheme,
                  auth_header_name: authHeader,
                  image_field: imageField,
                  identity_field: identityField || null,
                  extra_form_fields: parsedExtraFields.value,
                  static_headers: parsedStaticHeaders.value,
                  response_identity_path: identityPath,
                  response_confidence_path: confidencePath || null,
                  response_correct_path: correctPath || null,
                  timeout_seconds: 30,
                  max_retries: 2,
                },
                fairness_threshold: Number(threshold),
                language,
              })
            }
          >
            <ShieldCheck />
            {t("task.createAndStart")}
          </button>
        </>
      }
    >
      <div className="form-grid">
        <div className="form-field full">
          <label htmlFor="task-dataset">{t("task.dataset")}</label>
          <select
            id="task-dataset"
            value={datasetId}
            onChange={(event) => setDatasetId(event.target.value)}
          >
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {datasetDisplayName(dataset, t)} · {dataset.sample_count}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="task-name">{t("task.taskName")}</label>
          <input
            id="task-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={t("task.taskPlaceholder")}
          />
        </div>
        <div className="form-field">
          <label htmlFor="task-algorithm">{t("task.algorithm")}</label>
          <input
            id="task-algorithm"
            value={algorithm}
            onChange={(event) => setAlgorithm(event.target.value)}
            placeholder={t("task.algorithmPlaceholder")}
          />
        </div>
        <div className="form-field full">
          <label htmlFor="task-endpoint">{t("task.endpoint")}</label>
          <input
            id="task-endpoint"
            value={endpoint}
            onChange={(event) => setEndpoint(event.target.value)}
            placeholder={t("task.endpointPlaceholder")}
          />
          <span className="field-hint">
            <Info />
            {t("task.localSimulator")}
          </span>
        </div>
        <div className="form-field">
          <label htmlFor="task-method">{t("task.method")}</label>
          <select
            id="task-method"
            value={method}
            onChange={(event) => setMethod(event.target.value)}
          >
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="task-threshold">{t("task.threshold")}</label>
          <input
            id="task-threshold"
            type="number"
            min="0"
            max="1"
            step="0.01"
            value={threshold}
            onChange={(event) => setThreshold(event.target.value)}
          />
        </div>
        <div className="form-field">
          <label htmlFor="task-auth-scheme">{t("task.authScheme")}</label>
          <select
            id="task-auth-scheme"
            value={authScheme}
            onChange={(event) => setAuthScheme(event.target.value)}
          >
            <option value="none">{t("task.authNone")}</option>
            <option value="bearer">{t("task.authBearer")}</option>
            <option value="header">{t("task.authHeader")}</option>
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="task-auth-header">{t("task.authHeaderName")}</label>
          <input
            id="task-auth-header"
            value={authHeader}
            disabled={authScheme === "none"}
            onChange={(event) => setAuthHeader(event.target.value)}
            placeholder={t("task.authHeaderPlaceholder")}
          />
        </div>
        <div className="form-field full">
          <label htmlFor="task-secret">{t("task.apiKey")}</label>
          <input
            id="task-secret"
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
          />
          <span className="field-hint">
            <ShieldCheck />
            {t("task.apiKeyHint")}
          </span>
        </div>
        <div className="form-field full provider-mapping">
          <button
            type="button"
            className="mapping-toggle"
            onClick={() => setShowMapping((current) => !current)}
            aria-expanded={showMapping}
          >
            {showMapping ? t("task.hideMapping") : t("task.showMapping")}
          </button>
          {showMapping ? (
            <div className="form-grid provider-mapping-fields">
              <div className="form-field">
                <label htmlFor="task-image-field">{t("task.imageField")}</label>
                <input id="task-image-field" value={imageField} onChange={(event) => setImageField(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="task-identity-field">{t("task.identityField")}</label>
                <input id="task-identity-field" value={identityField} onChange={(event) => setIdentityField(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="task-identity-path">{t("task.identityPath")}</label>
                <input id="task-identity-path" value={identityPath} onChange={(event) => setIdentityPath(event.target.value)} />
              </div>
              <div className="form-field">
                <label htmlFor="task-confidence-path">{t("task.confidencePath")}</label>
                <input id="task-confidence-path" value={confidencePath} onChange={(event) => setConfidencePath(event.target.value)} />
              </div>
              <div className="form-field full">
                <label htmlFor="task-correct-path">{t("task.correctPath")}</label>
                <input id="task-correct-path" value={correctPath} onChange={(event) => setCorrectPath(event.target.value)} />
                <span className="field-hint"><Info />{t("task.mappingHint")}</span>
              </div>
              <div className="form-field">
                <label htmlFor="task-extra-fields">{t("task.extraFields")}</label>
                <textarea id="task-extra-fields" value={extraFields} onChange={(event) => setExtraFields(event.target.value)} aria-invalid={!parsedExtraFields.valid} />
              </div>
              <div className="form-field">
                <label htmlFor="task-static-headers">{t("task.staticHeaders")}</label>
                <textarea id="task-static-headers" value={staticHeaders} onChange={(event) => setStaticHeaders(event.target.value)} aria-invalid={!parsedStaticHeaders.valid} />
              </div>
              {!parsedExtraFields.valid || !parsedStaticHeaders.valid ? <div className="field-hint full"><Info />{t("task.jsonMapError")}</div> : null}
            </div>
          ) : null}
        </div>
        <div className="form-field">
          <label htmlFor="task-language">{t("task.language")}</label>
          <select
            id="task-language"
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          >
            <option value="zh">{t("topbar.zh")}</option>
            <option value="en">{t("topbar.en")}</option>
          </select>
        </div>
      </div>
    </Modal>
  );
}

function parseStringMap(source: string): { value: Record<string, string>; valid: boolean } {
  try {
    const value: unknown = JSON.parse(source || "{}");
    if (!value || Array.isArray(value) || typeof value !== "object") return { value: {}, valid: false };
    const entries = Object.entries(value);
    if (entries.some(([key, item]) => !key || typeof item !== "string")) return { value: {}, valid: false };
    return { value: Object.fromEntries(entries), valid: true };
  } catch {
    return { value: {}, valid: false };
  }
}
