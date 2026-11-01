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


## Publish the review website

Build the portable website with:

```bash
cd apps/web
npm ci
npm run build:review
```

The generated `docs/` folder is committed so Anonymous GitHub can serve the same
HTML, CSS and JavaScript as GitHub Pages. Its links are relative, so it works
under either hosting URL. Commit and push this folder together with source
changes; the Pages workflow also rebuilds and commits it after source pushes to
`main_annonymous`.

In GitHub, open **Settings → Pages** and choose **Deploy from a branch**,
`main_annonymous`, and `/docs`. The workflow uploads and deploys the same folder
after building it. This also deploys updates when its generated commit uses
`GITHUB_TOKEN`, which does not trigger GitHub's branch publishing workflow.

In **Settings → Environments → github-pages**, restrict deployment branches to
`main_annonymous`. This repository's Pages site is reserved for review until the
normal publishing settings are restored. Only `main_annonymous` can run the
review Pages build and deploy jobs. The original `main` branch's Pages workflow
must have its push trigger disabled as well; branch-local workflow edits alone
cannot stop a workflow defined on another branch.

At Anonymous GitHub, select `main_annonymous` and enable **Auto-update from
GitHub**, **GitHub Pages**, **Display images**, and **Keep links**. Share the
service's website link with reviewers. The direct GitHub Pages URL identifies
the repository owner. Inspect the anonymous site's navigation, leaderboard,
model and dataset dialogs before sharing it; its proxy applies its own content
rewriting and browser restrictions.

To preview the portable files locally:

```bash
python3 -m http.server 8000 --directory docs
```

Run that command from the repository root, then open `http://localhost:8000`.

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
the review package. The Contribute page supports local proposal drafts and previews; identifying
repository and submission links are replaced with placeholders.
