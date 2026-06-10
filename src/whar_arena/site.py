import json
from pathlib import Path
from typing import Any

from whar_arena.catalog import export_catalog
from whar_arena.paths import WEB_GENERATED_DIR
from whar_arena.planner import plan_runs, planned_runs_as_dicts
from whar_arena.protocol import load_protocol
from whar_arena.results import load_results


def export_site_data(output_dir: Path = WEB_GENERATED_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol = load_protocol()
    catalog = export_catalog()
    plan = planned_runs_as_dicts(plan_runs(protocol=protocol))
    results = load_results()
    payload = {
        "protocol": {
            "id": protocol.id,
            "hash": protocol.digest,
            "name": protocol.data.get("name", protocol.id),
            "split_count": len(protocol.split_ids),
            "data": protocol.data,
        },
        "catalog": catalog,
        "plan": plan,
        "results": results,
    }

    for name, value in payload.items():
        (output_dir / f"{name}.json").write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n"
        )
    return payload
