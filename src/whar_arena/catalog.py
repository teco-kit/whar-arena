from dataclasses import asdict, dataclass
from typing import Any

from whar_datasets import BENCHMARK_DATASET_IDS, get_dataset_cfg
from whar_models import list_models


@dataclass(frozen=True)
class DatasetEntry:
    id: str
    name: str
    package: str = "whar-datasets"


@dataclass(frozen=True)
class ModelEntry:
    id: str
    name: str
    family: str
    framework: str
    paper: str | None
    package: str = "whar-models"


def discover_datasets() -> list[DatasetEntry]:
    entries: list[DatasetEntry] = []
    for dataset_id in BENCHMARK_DATASET_IDS:
        cfg = get_dataset_cfg(dataset_id)
        name = getattr(cfg, "name", None) or dataset_id.value.replace("_", " ").title()
        entries.append(DatasetEntry(id=dataset_id.value, name=str(name)))
    return sorted(entries, key=lambda entry: entry.id)


def discover_models() -> list[ModelEntry]:
    return [
        ModelEntry(
            id=spec.id,
            name=spec.name,
            family=spec.family,
            framework=spec.framework,
            paper=spec.paper,
        )
        for spec in list_models()
    ]


def export_catalog() -> dict[str, Any]:
    return {
        "datasets": [asdict(entry) for entry in discover_datasets()],
        "models": [asdict(entry) for entry in discover_models()],
    }
