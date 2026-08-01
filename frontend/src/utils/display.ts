import type { TFunction } from "i18next";
import type { Dataset, EvaluationTask } from "../api/types";

const SEEDED_DEMO_ALGORITHMS = new Set([
  "CityVision Face API v4.2",
  "CivicID Recognition 3.8",
  "MetroSecure CV 2.1",
  "NorthStar Edge 1.6",
]);

/** Localize system-owned demo records while preserving user-entered text. */
export function datasetDisplayName(dataset: Dataset, t: TFunction): string {
  return dataset.is_demo ? t("dataset.demoName") : dataset.name;
}

export function datasetDisplayDescription(
  dataset: Dataset,
  t: TFunction,
): string {
  return dataset.is_demo ? t("dataset.demoDescription") : dataset.description;
}

export function isSeededDemoTask(task: EvaluationTask): boolean {
  return SEEDED_DEMO_ALGORITHMS.has(task.algorithm_name);
}

export function taskDisplayName(task: EvaluationTask, t: TFunction): string {
  return isSeededDemoTask(task)
    ? t("task.demoReviewName", { algorithm: task.algorithm_name })
    : task.name;
}
