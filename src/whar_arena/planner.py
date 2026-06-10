import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from whar_datasets import WHARDatasetID, get_dataset_cfg

from whar_arena.catalog import DatasetEntry, ModelEntry, discover_datasets, discover_models
from whar_arena.paths import RESULTS_DIR
from whar_arena.protocol import Protocol, load_protocol


@dataclass(frozen=True)
class PlannedRun:
    protocol_id: str
    protocol_hash: str
    model_id: str
    dataset_id: str
    split_id: str
    fingerprint: str
    result_path: str
    status: str


def fingerprint_run(
    protocol: Protocol,
    model: ModelEntry,
    dataset: DatasetEntry,
    split_id: str,
) -> str:
    payload = {
        "protocol_id": protocol.id,
        "protocol_hash": protocol.digest,
        "model_id": model.id,
        "dataset_id": dataset.id,
        "split_id": split_id,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def result_path_for(protocol_id: str, model_id: str, dataset_id: str, split_id: str) -> Path:
    return RESULTS_DIR / protocol_id / model_id / dataset_id / f"{split_id}.json"


def plan_runs(
    *,
    protocol: Protocol | None = None,
    only_model: str | None = None,
    only_dataset: str | None = None,
) -> list[PlannedRun]:
    protocol = protocol or load_protocol()
    models = [model for model in discover_models() if only_model in (None, model.id)]
    datasets = [
        dataset for dataset in discover_datasets() if only_dataset in (None, dataset.id)
    ]

    runs: list[PlannedRun] = []
    for model in models:
        for dataset in datasets:
            for split_id in split_ids_for_dataset(protocol, dataset):
                fingerprint = fingerprint_run(protocol, model, dataset, split_id)
                path = result_path_for(protocol.id, model.id, dataset.id, split_id)
                status = "complete" if _result_matches(path, fingerprint) else "missing"
                runs.append(
                    PlannedRun(
                        protocol_id=protocol.id,
                        protocol_hash=protocol.digest,
                        model_id=model.id,
                        dataset_id=dataset.id,
                        split_id=split_id,
                        fingerprint=fingerprint,
                        result_path=str(path.relative_to(RESULTS_DIR.parent.parent)),
                        status=status,
                    )
                )
    return runs


def split_ids_for_dataset(protocol: Protocol, dataset: DatasetEntry) -> list[str]:
    split_count = int(protocol.data["split"]["k"])
    if protocol.data["split"]["strategy"] == "k_subject_groups":
        cfg = get_dataset_cfg(WHARDatasetID(dataset.id))
        split_count = min(split_count, int(cfg.num_of_subjects))
    return [f"split-{index:02d}" for index in range(split_count)]


def _result_matches(path: Path, fingerprint: str) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False
    return data.get("fingerprint") == fingerprint and data.get("status") == "complete"


def planned_runs_as_dicts(runs: list[PlannedRun]) -> list[dict[str, str]]:
    return [asdict(run) for run in runs]
