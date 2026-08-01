import { api } from "./client";
import type {
  ApiResponse,
  Dataset,
  EvaluationTask,
  FailedSample,
  Paginated,
  ReportRecord,
  Sample,
} from "./types";
import type { SessionUser } from "../store/session";

export const authApi = {
  setupStatus: async () =>
    (
      await api.get<
        ApiResponse<{
          setup_required: boolean;
          demo_login_available: boolean;
          default_admin_email: string | null;
        }>
      >("/auth/setup-status")
    ).data.data,
  bootstrap: async (payload: { email: string; display_name: string; password: string }) =>
    (await api.post<ApiResponse<{ access_token: string; expires_in: number; user: SessionUser }>>("/auth/bootstrap", payload)).data.data,
  login: async (payload: { email: string; password: string }) =>
    (await api.post<ApiResponse<{ access_token: string; expires_in: number; user: SessionUser }>>("/auth/login", payload)).data.data,
  localSession: async () =>
    (await api.post<ApiResponse<{ access_token: string; expires_in: number; user: SessionUser }>>("/auth/local-session")).data.data,
  me: async () => (await api.get<ApiResponse<SessionUser>>("/auth/me")).data.data,
};

export const datasetApi = {
  list: async (search = "", page = 1) =>
    (
      await api.get<ApiResponse<Paginated<Dataset>>>("/datasets", {
        params: { search, page, page_size: 10 },
      })
    ).data.data,
  samples: async (datasetId: string, page = 1) =>
    (
      await api.get<ApiResponse<Paginated<Sample>>>(
        `/datasets/${datasetId}/samples`,
        { params: { page, page_size: 24 } },
      )
    ).data.data,
  upload: async (
    payload: { name: string; description: string; files: File[] },
    onProgress: (progress: number) => void,
  ) => {
    const form = new FormData();
    form.set("name", payload.name);
    form.set("description", payload.description);
    payload.files.forEach((file) => form.append("files", file));
    return (
      await api.post<ApiResponse<Dataset>>("/datasets/upload", form, {
        onUploadProgress: (event) =>
          onProgress(
            event.total ? Math.round((event.loaded / event.total) * 100) : 0,
          ),
      })
    ).data.data;
  },
  updateLabels: async (
    datasetId: string,
    sampleId: string,
    payload: Record<string, string>,
  ) =>
    (
      await api.patch<ApiResponse<Sample>>(
        `/datasets/${datasetId}/samples/${sampleId}/labels`,
        payload,
      )
    ).data.data,
  remove: async (datasetId: string) =>
    (await api.delete<ApiResponse<{ dataset_id: string; deleted: boolean }>>(`/datasets/${datasetId}`)).data.data,
  imageBlob: async (contentPath: string) =>
    (await api.get<Blob>(contentPath, { responseType: "blob" })).data,
};

export const taskApi = {
  list: async (page = 1) =>
    (
      await api.get<ApiResponse<Paginated<EvaluationTask>>>("/tasks", {
        params: { page, page_size: 20 },
      })
    ).data.data,
  create: async (payload: Record<string, unknown>) =>
    (await api.post<ApiResponse<EvaluationTask>>("/tasks", payload)).data.data,
  remove: async (taskId: string) =>
    (await api.delete<ApiResponse<{ task_id: string; deleted: boolean }>>(`/tasks/${taskId}`)).data.data,
  failed: async (taskId: string) =>
    (
      await api.get<ApiResponse<FailedSample[]>>(
        `/tasks/${taskId}/failed-samples`,
      )
    ).data.data,
  retry: async (taskId: string, apiKey: string) =>
    (
      await api.post<ApiResponse<Record<string, unknown>>>(
        `/tasks/${taskId}/retry-failed`,
        { api_key: apiKey },
      )
    ).data.data,
};

export const statsApi = {
  overview: async () =>
    (
      await api.get<
        ApiResponse<{
          dataset_count: number;
          task_count: number;
          completed_count: number;
          failed_sample_count: number;
          compliance_rate: number;
        }>
      >("/stats/overview")
    ).data.data,
  compare: async (datasetId: string) =>
    (
      await api.get<
        ApiResponse<{
          dataset_id: string;
          series: Array<{
            task_id: string;
            algorithm_name: string;
            status: string;
            metrics: EvaluationTask["metrics"];
          }>;
        }>
      >("/stats/compare", { params: { dataset_id: datasetId } })
    ).data.data,
};

export interface ReportPayload {
  task_id: string;
  language: string;
  title: string;
  include_failed_samples: boolean;
  include_methodology: boolean;
  issuing_authority: string;
  signer: string;
}

export const reportApi = {
  list: async () =>
    (await api.get<ApiResponse<ReportRecord[]>>("/reports")).data.data,
  create: async (payload: ReportPayload) =>
    (await api.post<ApiResponse<ReportRecord>>("/reports", payload)).data.data,
};
