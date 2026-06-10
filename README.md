# WHAR Arena

WHAR Arena is a Git-native benchmark and website for wearable human activity
recognition. The arena has one official protocol, discovers datasets from
`whar-datasets`, discovers models from `whar-models`, plans the full benchmark
matrix, and renders committed result files as a static website.

## Core Idea

```text
official protocol
x all benchmark datasets from whar-datasets
x all registered models from whar-models
= benchmark matrix
```

Every planned run receives a deterministic fingerprint. If a matching result
already exists, the run is skipped. When a dataset or model is added upstream,
the planner detects the new matrix entries automatically.

## Quick Start

```bash
uv sync --all-extras
uv pip install -e ../whar-datasets -e ../whar-models
uv run whar-arena catalog
uv run whar-arena plan --limit 10
uv run whar-arena export-site-data

cd apps/web
npm install
npm run dev
```

The first implementation includes a planner and static site renderer. The heavy
training runner is intentionally separated behind `whar-arena run`, so CI can
validate submissions cheaply and execute missing runs in dedicated jobs.
