from services.stats_service import calculate_fairness_metrics


def test_calculates_group_gap_and_compliance() -> None:
    records = [
        {
            "gender": "female",
            "age_group": "18-29",
            "ethnicity": "east_asian",
            "is_correct": True,
        },
        {
            "gender": "female",
            "age_group": "30-44",
            "ethnicity": "east_asian",
            "is_correct": True,
        },
        {
            "gender": "male",
            "age_group": "18-29",
            "ethnicity": "black",
            "is_correct": False,
        },
        {
            "gender": "male",
            "age_group": "30-44",
            "ethnicity": "black",
            "is_correct": True,
        },
    ]

    metrics = calculate_fairness_metrics(records, threshold=0.20)

    assert metrics["overall_accuracy"] == 0.75
    assert metrics["max_group_gap"] == 0.5
    assert metrics["is_compliant"] is False
    assert metrics["evaluated_samples"] == 4
    assert set(metrics["dimensions"]) == {"gender", "age_group", "ethnicity"}


def test_empty_records_are_non_compliant() -> None:
    metrics = calculate_fairness_metrics([], threshold=0.10)

    assert metrics["overall_accuracy"] == 0.0
    assert metrics["groups"] == []
    assert metrics["is_compliant"] is False
