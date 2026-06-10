# Contributing Benchmark Entries

WHAR Arena uses pull requests as the submission interface.

## New Models

Add the implementation to `whar-models` and register it in that package. Once
the model appears in `whar_models.list_models()`, WHAR Arena automatically plans
the model against every benchmark dataset in the official protocol.

Local check:

```bash
uv run whar-arena plan --only-model tinyhar --only-missing
```

## New Datasets

Add the dataset to `whar-datasets` and include it in
`BENCHMARK_DATASET_IDS` when it is eligible for the official benchmark. Once it
appears there, WHAR Arena automatically plans every registered model against it.

Local check:

```bash
uv run whar-arena plan --only-dataset actrectut_gestures --only-missing
```

## Results

Results are file based and validated with `schemas/result.schema.json`.
Official results should be produced by the benchmark runner. Manual result files
should be clearly marked in their `source.kind` and are not treated as official
unless maintainers approve them.

```bash
uv run whar-arena validate-results
uv run whar-arena export-site-data
```
