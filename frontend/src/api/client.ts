import axios, { type InternalAxiosRequestConfig } from "axios";
import { sessionStore, type SessionUser } from "../store/session";

interface ApiResponse<T> {
  data: T;
}

interface LocalSessionResult {
  access_token: string;
  user: SessionUser;
}

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _fairbenchSessionRetried?: boolean;
};

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  timeout: 45_000,
});

let localSessionRenewal: Promise<string | null> | null = null;

async function renewLocalSession(): Promise<string | null> {
  if (localSessionRenewal) return localSessionRenewal;

  localSessionRenewal = axios
    .post<ApiResponse<LocalSessionResult>>(
      `${api.defaults.baseURL}/auth/local-session`,
      undefined,
      { timeout: api.defaults.timeout },
    )
    .then(({ data }) => {
      sessionStore.setAuth(data.data.access_token, data.data.user);
      return data.data.access_token;
    })
    .catch(() => null)
    .finally(() => {
      localSessionRenewal = null;
    });

  return localSessionRenewal;
}

api.interceptors.request.use((config) => {
  const token = sessionStore.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401 && error.config) {
      const request = error.config as RetryableRequestConfig;
      const requestUrl = String(request.url ?? "");
      const isSessionEndpoint = requestUrl.includes("/auth/");

      if (!request._fairbenchSessionRetried && !isSessionEndpoint) {
        request._fairbenchSessionRetried = true;
        const accessToken = await renewLocalSession();
        if (accessToken) {
          request.headers.Authorization = `Bearer ${accessToken}`;
          return api.request(request);
        }
      }
    }

    window.dispatchEvent(
      new CustomEvent("fairbench:api-error", {
        detail: error,
      }),
    );
    return Promise.reject(error);
  },
);

export const downloadUrl = (path: string) =>
  `${api.defaults.baseURL ?? ""}${path}`;

export async function downloadFile(path: string, filename: string) {
  const payload = await api.get<Blob>(path, { responseType: "blob" });
  const url = URL.createObjectURL(payload.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
