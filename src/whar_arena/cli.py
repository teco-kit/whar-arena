import argparse
import json
import sys
from pathlib import Path

from whar_arena.catalog import export_catalog
from whar_arena.planner import plan_runs, planned_runs_as_dicts
from whar_arena.results import validate_results
from whar_arena.site import export_site_data
from whar_arena.training import run_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="whar-arena")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("catalog")

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--only-model")
    plan_parser.add_argument("--only-dataset")
    plan_parser.add_argument("--only-missing", action="store_true")
    plan_parser.add_argument("--limit", type=int)

    subparsers.add_parser("validate-results")
    subparsers.add_parser("export-site-data")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--only-model")
    run_parser.add_argument("--only-dataset")
    run_parser.add_argument("--limit", type=int, default=1)
    run_parser.add_argument("--datasets-dir", default="./datasets")
    run_parser.add_argument("--output-dir", default="./runs")
    run_parser.add_argument("--max-epochs", type=int)
    run_parser.add_argument("--patience", type=int)
    run_parser.add_argument("--limit-splits", type=int)

    args = parser.parse_args(argv)

    if args.command == "catalog":
        print(json.dumps(export_catalog(), indent=2, sort_keys=True))
        return 0

    if args.command == "plan":
        runs = plan_runs(only_model=args.only_model, only_dataset=args.only_dataset)
        if args.only_missing:
            runs = [run for run in runs if run.status == "missing"]
        if args.limit is not None:
            runs = runs[: args.limit]
        print(json.dumps(planned_runs_as_dicts(runs), indent=2, sort_keys=True))
        return 0

    if args.command == "validate-results":
        errors = validate_results()
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print("All result files are valid.")
        return 0

    if args.command == "export-site-data":
        payload = export_site_data()
        print(
            f"Exported {len(payload['catalog']['models'])} models, "
            f"{len(payload['catalog']['datasets'])} datasets, "
            f"{len(payload['results'])} result files."
        )
        return 0

    if args.command == "run":
        runs = [
            run
            for run in plan_runs(only_model=args.only_model, only_dataset=args.only_dataset)
            if run.status == "missing"
        ]
        pairs: list[tuple[str, str]] = []
        seen_pairs: set[tuple[str, str]] = set()
        for run in runs:
            pair = (run.model_id, run.dataset_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            pairs.append(pair)
        if args.limit is not None:
            pairs = pairs[: args.limit]
        if not pairs:
            print("No missing runs.")
            return 0

        selected_pairs = set(pairs)
        selected_runs = [
            run for run in runs if (run.model_id, run.dataset_id) in selected_pairs
        ]
        print(json.dumps(planned_runs_as_dicts(selected_runs), indent=2, sort_keys=True))
        for model_id, dataset_id in pairs:
            pair_output_dir = Path(args.output_dir) / f"{model_id}-{dataset_id}"
            metrics = run_benchmark(
                model_id=model_id,
                dataset_id=dataset_id,
                datasets_dir=Path(args.datasets_dir),
                output_dir=pair_output_dir,
                max_epochs=args.max_epochs,
                patience=args.patience,
                limit_splits=args.limit_splits,
                skip_existing=True,
            )
            print(
                f"Completed {model_id}/{dataset_id}: wrote {len(metrics)} new split result(s)."
            )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
