import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Sample } from "../../api/types";
import { Modal } from "../common/Modal";

interface SampleLabelModalProps {
  sample: Sample | null;
  pending: boolean;
  onClose: () => void;
  onSave: (payload: Record<string, string>) => void;
}

export function SampleLabelModal({
  sample,
  pending,
  onClose,
  onSave,
}: SampleLabelModalProps) {
  const { t } = useTranslation();
  const [ageGroup, setAgeGroup] = useState("");
  const [gender, setGender] = useState("");
  const [ethnicity, setEthnicity] = useState("");
  const [identity, setIdentity] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (!sample) return;
    const labels = sample.effective_labels;
    setAgeGroup(labels?.age_group ?? "");
    setGender(labels?.gender ?? "");
    setEthnicity(labels?.ethnicity ?? "");
    setIdentity(sample.ground_truth_identity ?? "");
    setReason("");
  }, [sample]);

  return (
    <Modal
      open={Boolean(sample)}
      title={t("dataset.manualReview")}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="button"
            disabled={pending}
            onClick={() =>
              onSave({
                age_group: ageGroup,
                gender,
                ethnicity,
                ground_truth_identity: identity,
                reason,
              })
            }
          >
            {t("dataset.saveCorrection")}
          </button>
        </>
      }
    >
      <div className="form-grid">
        <div className="form-field">
          <label htmlFor="sample-age">{t("dataset.ageGroup")}</label>
          <select
            id="sample-age"
            value={ageGroup}
            onChange={(event) => setAgeGroup(event.target.value)}
          >
            <option value="" disabled>{t("dataset.selectLabel")}</option>
            {["18-29", "30-44", "45-59", "60+"].map((value) => (
              <option key={value} value={value}>
                {t(`labels.${value}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="sample-gender">{t("dataset.gender")}</label>
          <select
            id="sample-gender"
            value={gender}
            onChange={(event) => setGender(event.target.value)}
          >
            <option value="" disabled>{t("dataset.selectLabel")}</option>
            {["female", "male", "non_binary"].map((value) => (
              <option key={value} value={value}>
                {t(`labels.${value}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="sample-ethnicity">{t("dataset.ethnicity")}</label>
          <select
            id="sample-ethnicity"
            value={ethnicity}
            onChange={(event) => setEthnicity(event.target.value)}
          >
            <option value="" disabled>{t("dataset.selectLabel")}</option>
            {["east_asian", "south_asian", "black", "white", "latino", "mena"].map(
              (value) => (
                <option key={value} value={value}>
                  {t(`labels.${value}`)}
                </option>
              ),
            )}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="sample-identity">{t("dataset.identity")}</label>
          <input
            id="sample-identity"
            value={identity}
            onChange={(event) => setIdentity(event.target.value)}
          />
        </div>
        <div className="form-field full">
          <label htmlFor="correction-reason">
            {t("dataset.correctionReason")}
          </label>
          <textarea
            id="correction-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder={t("dataset.reasonPlaceholder")}
            required
            minLength={3}
            maxLength={500}
          />
        </div>
      </div>
    </Modal>
  );
}
