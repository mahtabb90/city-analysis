import json
from pathlib import Path


def _project_root() -> Path:
    """
    Return the project root folder.

    tests/ is located at <root>/tests, so parents[1] = root.
    """
    return Path(__file__).resolve().parents[1]


def test_recommendations_json_file_exists() -> None:
    json_path = _project_root() / "data" / "comments.json"
    assert json_path.exists(), (
        "Missing file: data/comments.json\n"
        "Create it and commit it to the repo so CI can load it."
    )


def test_recommendations_json_is_valid_json() -> None:
    json_path = _project_root() / "data" / "comments.json"
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict), "Top-level JSON must be an object/dict."


def test_recommendations_json_has_expected_structure() -> None:
    json_path = _project_root() / "data" / "comments.json"
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Top-level keys
    assert "weather" in data, "JSON must contain top-level key: 'weather'"
    assert "traffic" in data, "JSON must contain top-level key: 'traffic'"

    weather_rules = data["weather"]
    traffic_rules = data["traffic"]

    assert isinstance(weather_rules, list), "'weather' must be a list"
    assert isinstance(traffic_rules, list), "'traffic' must be a list"
    assert len(weather_rules) > 0, "'weather' list must not be empty"
    assert len(traffic_rules) > 0, "'traffic' list must not be empty"

    # Validate weather rules
    for i, rule in enumerate(weather_rules):
        assert isinstance(rule, dict), f"weather[{i}] must be an object/dict"

        for key in ("condition", "temperature_min", "temperature_max", "comments"):
            assert key in rule, f"weather[{i}] missing key: '{key}'"

        assert (
            isinstance(rule["condition"], str) and rule["condition"].strip()
        ), f"weather[{i}].condition must be a non-empty string"
        assert isinstance(
            rule["temperature_min"], (int, float)
        ), f"weather[{i}].temperature_min must be a number"
        assert isinstance(
            rule["temperature_max"], (int, float)
        ), f"weather[{i}].temperature_max must be a number"
        assert (
            rule["temperature_min"] <= rule["temperature_max"]
        ), f"weather[{i}] invalid range: temperature_min > temperature_max"

        comments = rule["comments"]
        assert (
            isinstance(comments, list) and len(comments) > 0
        ), f"weather[{i}].comments must be a non-empty list"
        for j, c in enumerate(comments):
            assert (
                isinstance(c, str) and c.strip()
            ), f"weather[{i}].comments[{j}] must be a non-empty string"

    # Validate traffic rules
    for i, rule in enumerate(traffic_rules):
        assert isinstance(rule, dict), f"traffic[{i}] must be an object/dict"

        for key in ("mode", "status", "comments"):
            assert key in rule, f"traffic[{i}] missing key: '{key}'"

        assert (
            isinstance(rule["mode"], str) and rule["mode"].strip()
        ), f"traffic[{i}].mode must be a non-empty string"
        assert (
            isinstance(rule["status"], str) and rule["status"].strip()
        ), f"traffic[{i}].status must be a non-empty string"

        comments = rule["comments"]
        assert (
            isinstance(comments, list) and len(comments) > 0
        ), f"traffic[{i}].comments must be a non-empty list"
        for j, c in enumerate(comments):
            assert (
                isinstance(c, str) and c.strip()
            ), f"traffic[{i}].comments[{j}] must be a non-empty string"
