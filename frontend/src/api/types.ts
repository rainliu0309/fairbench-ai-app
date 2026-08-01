export interface BilingualMessage {
  zh: string;
  en: string;
}

export interface ApiResponse<T> {
  data: T;
  message: BilingualMessage;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  status: string;
  sample_count: number;
  is_demo: boolean;
  created_at: string;
}

export interface Labels {
  age_group: string;
  gender: string;
  ethnicity: string;
  confidence?: number;
}

export interface Sample {
  id: string;
  dataset_id: string;
  filename: string;
  content_type: string;
  ground_truth_identity: string | null;
  agnes_labels: Labels | null;
  manual_labels: Labels | null;
  effective_labels: Labels | null;
  label_source: string;
  label_status: string;
  annotation_error: string | null;
  preview_url: string | null;
  created_at: string;
}

export interface GroupMetric {
  dimension: "gender" | "age_group" | "ethnicity";
  group: string;
  accuracy: number;
  sample_count: number;
  gap_from_overall: number;
}

export interface Metrics {
  overall_accuracy: number;
  max_group_gap: number;
  bias_coefficient: number;
  std_deviation: number;
  threshold: number;
  is_compliant: boolean;
  evaluated_samples: number;
  groups: GroupMetric[];
  dimensions: Record<string, GroupMetric[]>;
}

export interface EvaluationTask {
  id: string;
  dataset_id: string;
  name: string;
  algorithm_name: string;
  target_api_url: string;
  target_api_method: string;
  target_api_config: Record<string, unknown> | null;
  status: string;
  progress: number;
  fairness_threshold: number;
  language: string;
  metrics: Metrics | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface FailedSample {
  id: string;
  task_id: string;
  sample_id: string;
  status: string;
  error_code: string | null;
  error_message: string | null;
  retry_count: number;
  updated_at: string;
}

export interface ReportRecord {
  id: string;
  task_id: string;
  report_no: string;
  title: string;
  language: string;
  parameters: Record<string, unknown> | null;
  checksum: string;
  created_at: string;
}
