import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();

  const changeLanguage = (language: string) => {
    void i18n.changeLanguage(language);
    localStorage.setItem("fairbench-language", language);
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  };

  const isEnglish = i18n.language.startsWith("en");
  const targetLanguage = isEnglish ? "zh" : "en";

  return (
    <button
      className={`language-switcher${isEnglish ? " is-english" : ""}`}
      type="button"
      role="switch"
      aria-checked={isEnglish}
      aria-label={t("topbar.language")}
      title={isEnglish ? t("topbar.zh") : t("topbar.en")}
      onClick={() => changeLanguage(targetLanguage)}
    >
      <Languages size={14} color="#7892ab" aria-hidden="true" />
      <span className="language-track" aria-hidden="true">
        <span className="language-track-label language-track-zh">中</span>
        <span className="language-track-label language-track-en">EN</span>
        <span className="language-thumb">{isEnglish ? "EN" : "中"}</span>
      </span>
    </button>
  );
}
