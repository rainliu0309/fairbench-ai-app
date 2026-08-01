import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import zh from "./locales/zh.json";

const savedLanguage = localStorage.getItem("fairbench-language") ?? "zh";

void i18n.use(initReactI18next).init({
  resources: {
    zh: { translation: zh },
    en: { translation: en },
  },
  lng: savedLanguage,
  fallbackLng: "zh",
  interpolation: { escapeValue: false },
});

export default i18n;
