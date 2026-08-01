const LANGUAGE_KEY = "fairbench-language";
const TOKEN_KEY = "fairbench-access-token";
const USER_KEY = "fairbench-user";

export interface SessionUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
}

export const sessionStore = {
  getLanguage: () => localStorage.getItem(LANGUAGE_KEY) ?? "zh",
  setLanguage: (language: string) => localStorage.setItem(LANGUAGE_KEY, language),
  getToken: () => sessionStorage.getItem(TOKEN_KEY),
  setAuth: (token: string, user: SessionUser) => {
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  getUser: (): SessionUser | null => {
    const value = sessionStorage.getItem(USER_KEY);
    try {
      return value ? (JSON.parse(value) as SessionUser) : null;
    } catch {
      return null;
    }
  },
  clearAuth: () => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  },
};
