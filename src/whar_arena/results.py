import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from whar_arena.paths import RESULTS_DIR, SCHEMA_DIR


def iter_result_files(results_dir: Path = RESULTS_DIR) -> list[Path]:
    if not results_dir.exists():
        return []
    return sorted(results_dir.glob("*/*/*/*.json"))


def load_results(results_dir: Path = RESULTS_DIR) -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in iter_result_files(results_dir)]


def validate_results(results_dir: Path = RESULTS_DIR) -> list[str]:
    schema = json.loads((SCHEMA_DIR / "result.schema.json").read_text())
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for path in iter_result_files(results_dir):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
            continue
        for error in validator.iter_errors(data):
            errors.append(f"{path}: {error.message}")
    return errors
