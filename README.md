# HARena

Anonymous review version of the wearable human activity recognition benchmark.
The static website includes the protocol, model and dataset catalogs, committed
results, and deployment measurements. Author information, affiliations,
acknowledgements, and project repository links are withheld during review.
Published model and dataset papers remain linked as benchmark references.

## Run the website

The website builds directly from the committed data and requires Node.js 24.
No Python packages, dataset downloads, or upstream repositories are needed.

```bash
cd apps/web
npm ci
npm run dev
```

Build a static copy with `npm run build`. The output is in `apps/web/dist`.
For a subdirectory deployment, set `PUBLIC_BASE_PATH` to the public path and
`PUBLIC_SITE_URL` to the anonymous hosting URL before building.

## Benchmark tools

Python benchmark tools require separate local copies of `whar-datasets` and
`whar-models` in sibling directories. Supply anonymous copies before running:

```bash
uv sync --all-extras
uv run whar-arena catalog
uv run whar-arena plan --limit 10
uv run whar-arena validate-results
uv run pytest
```

The Python lockfile is omitted because it contained identifying upstream source
URLs. `uv sync` resolves the supplied local packages. The optional benchmark
workflow requires `DATASET_REPOSITORY` and `MODEL_REPOSITORY` repository variables
pointing to anonymous copies of those packages.

## Share for review

Use an anonymous host for the static output, or an anonymous repository created
from a source export without `.git`. This branch inherits the original Git
history and remote configuration; publishing it in the original repository
reveals ownership and commit authors. Export files without history with:

```bash
git archive --format=zip HEAD -o ../anonymous-review.zip
```

Commit the anonymized changes before using `git archive`. Do not include local
Git metadata, dependency directories, caches, or generated Python lockfiles in
the review package. Contributions are paused in the review website.
