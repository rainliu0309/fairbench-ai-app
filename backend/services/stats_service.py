from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


GROUP_DIMENSIONS = ("gender", "age_group", "ethnicity")


def calculate_fairness_metrics(
    records: list[dict[str, Any]], threshold: float
) -> dict[str, Any]:
    """Calculate independently testable fairness metrics using effective labels."""
    if not records:
        return {
            "overall_accuracy": 0.0,
            "max_group_gap": 0.0,
            "bias_coefficient": 0.0,
            "std_deviation": 0.0,
            "threshold": threshold,
            "is_compliant": False,
            "evaluated_samples": 0,
            "groups": [],
            "dimensions": {},
        }

    frame = pd.DataFrame(records)
    frame["is_correct"] = frame["is_correct"].astype(float)
    overall_accuracy = float(frame["is_correct"].mean())
    all_groups: list[dict[str, Any]] = []
    dimensions: dict[str, list[dict[str, Any]]] = {}

    for dimension in GROUP_DIMENSIONS:
        if dimension not in frame:
            continue
        grouped = (
            frame.groupby(dimension, dropna=False)["is_correct"]
            .agg(["mean", "count"])
            .reset_index()
        )
        dimension_rows = []
        for row in grouped.to_dict("records"):
            accuracy = float(row["mean"])
            entry = {
                "dimension": dimension,
                "group": str(row[dimension]),
                "accuracy": round(accuracy, 4),
                "sample_count": int(row["count"]),
                "gap_from_overall": round(abs(accuracy - overall_accuracy), 4),
            }
            dimension_rows.append(entry)
            all_groups.append(entry)
        dimensions[dimension] = dimension_rows

    accuracies = np.array([row["accuracy"] for row in all_groups], dtype=float)
    max_gap = float(accuracies.max() - accuracies.min()) if accuracies.size else 0.0
    std_deviation = float(np.std(accuracies)) if accuracies.size else 0.0
    bias_coefficient = (
        float(max_gap / max(overall_accuracy, 1e-9)) if accuracies.size else 0.0
    )

    return {
        "overall_accuracy": round(overall_accuracy, 4),
        "max_group_gap": round(max_gap, 4),
        "bias_coefficient": round(bias_coefficient, 4),
        "std_deviation": round(std_deviation, 4),
        "threshold": threshold,
        "is_compliant": max_gap <= threshold,
        "evaluated_samples": int(len(frame)),
        "groups": all_groups,
        "dimensions": dimensions,
    }
