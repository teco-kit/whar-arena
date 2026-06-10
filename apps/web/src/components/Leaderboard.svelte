<script lang="ts">
  import datasetDetailsData from "../generated/dataset-details.json";
  import modelDetailsData from "../generated/model-details.json";
  import paperLinks from "../generated/paper-links.json";

  type Dataset = {
    id: string;
    name: string;
  };
  type Model = {
    id: string;
    name: string;
    family: string;
    framework: string;
  };
  type Catalog = {
    datasets: Dataset[];
    models: Model[];
  };
  type Result = {
    model_id: string;
    dataset_id: string;
    split_id: string;
    status: string;
    metrics: Record<string, number | null>;
  };
  type LeaderboardRow = Model & {
    rank: number | null;
    netImprovement: number | null;
    netImprovementCi95: number | null;
    macroF1: number | null;
    modelSizeMb: number | null;
    modelSizeIndex: number | null;
  };
  type MatrixCell = {
    modelId: string;
    macroF1: number | null;
  };
  type DeploymentPoint = {
    model_id: string;
    benchmark_model_name: string;
    name: string;
    family: string;
    mean_test_macro_f1: number | null;
    mean_latency_ms: number | null;
    mean_peak_pss_delta_mb: number | null;
    exported_model_size_mb: number | null;
    deployment_measurements: number;
    deployment_dataset_count: number;
    color: string;
  };
  type DeploymentTradeoffs = {
    source: {
      kind: string;
      snapshot_date: string;
      notes: string;
    };
    points: DeploymentPoint[];
  };
  type PaperLink = {
    title: string;
    url: string;
  };
  type ModelAuthor = {
    name: string;
    affiliation: string;
  };
  type ModelDetail = {
    params: string | null;
    flops: string | null;
    institutions: string[];
    authors: ModelAuthor[];
  };
  type ModelDetailsData = {
    source: {
      table: string;
      input_assumption: string;
      note: string;
    };
    models: Record<string, ModelDetail>;
  };
  type DatasetDetail = {
    year: number;
    citations: number;
    subjects: number;
    activities: number;
    settings: string;
    deviceTypes: string;
    sensorModalities: string;
    channels: number;
  };
  type DatasetDetailsData = {
    source: {
      table: string;
      note: string;
      abbreviations: string;
    };
    datasets: Record<string, DatasetDetail>;
  };
  type SortKey = "rank" | "family" | "net_improvement" | "macro_f1" | "model_size";
  type SortDirection = "asc" | "desc";
  type ScatterMetric =
    | "mean_latency_ms"
    | "mean_peak_pss_delta_mb"
    | "exported_model_size_mb";
  type ScatterConfig = {
    metric: ScatterMetric;
    title: string;
    xLabel: string;
  };
  type ScatterPoint = DeploymentPoint & {
    x: number;
    y: number;
  };
  type ScatterPlot = ScatterConfig & {
    points: ScatterPoint[];
    xMax: number;
    yMin: number;
    yMax: number;
    xTicks: number[];
    yTicks: number[];
    missingCount: number;
  };
  type FilterOption = {
    id: string;
    name: string;
  };

  let {
    catalog,
    deploymentTradeoffs = null,
    results,
  }: {
    catalog: Catalog;
    deploymentTradeoffs?: DeploymentTradeoffs | null;
    results: Result[];
  } = $props();

  const familyOrder = ["attn", "cnn", "dense", "rnn", "graph", "spec", "fe"];
  const familyPartsById: Record<string, string[]> = {
    attn_cnn_dense: ["attn", "cnn", "dense"],
    attn_cnn_dense_rnn: ["attn", "cnn", "dense", "rnn"],
    classical_ml: ["fe"],
    cnn: ["cnn"],
    cnn_dense_graph: ["cnn", "dense", "graph"],
    cnn_dense_rnn: ["cnn", "dense", "rnn"],
    compact_neural: ["attn", "cnn", "dense", "rnn"],
    dense: ["dense"],
    dense_rnn: ["dense", "rnn"],
    dense_spec: ["dense", "spec"],
    fe: ["fe"],
    neural: ["neural"],
  };
  const classicalBaselineIds = new Set(["knn", "random_forest", "svm"]);

  let selectedDatasetIds = $state(catalog.datasets.map((item) => item.id));
  let selectedModelFamilyIds = $state(getModelFamilyIds(catalog.models));
  let selectedModelIds = $state(catalog.models.map((item) => item.id));
  let selectedDetailModelId = $state<string | null>(null);
  let selectedDetailDatasetId = $state<string | null>(null);
  let sortKey = $state<SortKey>("rank");
  let sortDirection = $state<SortDirection>("asc");

  const datasetDetails = datasetDetailsData as DatasetDetailsData;
  const datasetDetailMap = datasetDetails.datasets;
  const modelDetails = modelDetailsData as ModelDetailsData;
  const detailMap = modelDetails.models;
  const linkMap = paperLinks as {
    datasets: Record<string, PaperLink>;
    models: Record<string, PaperLink>;
  };
  const plotBox = {
    width: 380,
    height: 270,
    left: 50,
    right: 18,
    top: 18,
    bottom: 46,
  };
  const scatterConfigs: ScatterConfig[] = [
    {
      metric: "mean_latency_ms",
      title: "Mean Test Macro-F1 vs Latency",
      xLabel: "Mean latency (ms)",
    },
    {
      metric: "mean_peak_pss_delta_mb",
      title: "Mean Test Macro-F1 vs Peak PSS Delta",
      xLabel: "Mean peak PSS delta (MB)",
    },
    {
      metric: "exported_model_size_mb",
      title: "Mean Test Macro-F1 vs Exported Model Size",
      xLabel: "Exported model size (MB)",
    },
  ];
  const highlightedScatterIds = new Set([
    "cnn_har",
    "tinyhar",
    "tinierhar",
    "random_forest",
    "dana",
    "triple_cross_domain_attention",
  ]);
  const numberFormatter = new Intl.NumberFormat("en-US");
  const metricInfo = {
    rank:
      "Rank is assigned by mean Macro-F1 over the currently selected datasets. Higher Macro-F1 ranks first.",
    netImprovement:
      "Net Improvement is the average Macro-F1 gain over the best classical model on each selected dataset. Error bars show a 95% confidence interval across dataset-level gains.",
    macroF1:
      "Macro-F1 is the unweighted mean of per-class F1 scores. The leaderboard averages Macro-F1 over the selected datasets.",
    modelSize:
      "Efficiency Score is the paper's model-size efficiency index: Macro-F1 and log model size are normalized across models, then combined so higher is better.",
  };

  const validResults = $derived(
    results.filter((result) => result.status === "complete" || result.status === "example"),
  );
  const selectedDatasetSet = $derived(new Set(selectedDatasetIds));
  const selectedModelFamilySet = $derived(new Set(selectedModelFamilyIds));
  const selectedModelSet = $derived(new Set(selectedModelIds));
  const modelFamilyOptions = $derived(getModelFamilyOptions(catalog.models));
  const selectedDatasetSummary = $derived(formatSelectedDatasetSummary());
  const selectedModelFamilySummary = $derived(formatSelectedModelFamilySummary());
  const selectedModelSummary = $derived(formatSelectedModelSummary());
  const selectedDetailModel = $derived(
    selectedDetailModelId
      ? catalog.models.find((item) => item.id === selectedDetailModelId) ?? null
      : null,
  );
  const selectedDetail = $derived(
    selectedDetailModelId ? getModelDetail(selectedDetailModelId) : null,
  );
  const selectedDetailDataset = $derived(
    selectedDetailDatasetId
      ? catalog.datasets.find((item) => item.id === selectedDetailDatasetId) ?? null
      : null,
  );
  const selectedDatasetDetail = $derived(
    selectedDetailDatasetId ? getDatasetDetail(selectedDetailDatasetId) : null,
  );
  const visibleModels = $derived(
    catalog.models.filter(
      (item) => selectedModelSet.has(item.id) && isFamilyAllowed(item.family),
    ),
  );

  const rows = $derived(
    withRanks(
      withModelSizeIndex(
        visibleModels.map((model) => {
          const scopedResults = validResults.filter(
            (result) =>
              result.model_id === model.id &&
              selectedDatasetSet.has(result.dataset_id),
          );
          const improvement = netImprovementStats(model.id);

          return {
            ...model,
            rank: null,
            netImprovement: improvement.mean,
            netImprovementCi95: improvement.ci95,
            macroF1: averageMetric(scopedResults, "macro_f1"),
            modelSizeMb: averageMetric(scopedResults, "exported_model_size_mb"),
            modelSizeIndex: averageMetric(scopedResults, "model_size_efficiency_index"),
          };
        }),
      ),
    ).sort(compareRows),
  );

  const netImprovementScale = $derived(getNetImprovementScale(rows));
  const deploymentPoints = $derived(
    deploymentTradeoffs?.points.filter(
      (point) => selectedModelSet.has(point.model_id) && isFamilyAllowed(point.family),
    ) ?? [],
  );
  const scatterPlots = $derived(scatterConfigs.map((config) => createScatterPlot(config)));
  const missingModelSizeNames = $derived(
    deploymentPoints
      .filter((point) => point.exported_model_size_mb === null)
      .map((point) => point.name)
      .join(", "),
  );

  const matrixRows = $derived(
    catalog.datasets
      .filter((item) => selectedDatasetSet.has(item.id))
      .map((item) => ({
        ...item,
        cells: visibleModels.map((model) => {
          const scopedResults = validResults.filter(
            (result) => result.dataset_id === item.id && result.model_id === model.id,
          );

          return {
            modelId: model.id,
            macroF1: averageMetric(scopedResults, "macro_f1"),
          };
        }),
      })),
  );

  function averageMetric(items: Result[], metric: string) {
    const values = items
      .map((result) => result.metrics[metric])
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value));

    if (values.length === 0) return null;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }

  function withRanks(baseRows: LeaderboardRow[]) {
    const ranked = [...baseRows].sort(compareByPerformanceRank);
    const rankById = new Map<string, number | null>();

    ranked.forEach((row, index) => {
      rankById.set(row.id, row.macroF1 === null ? null : index + 1);
    });

    return baseRows.map((row) => ({
      ...row,
      rank: rankById.get(row.id) ?? null,
    }));
  }

  function compareByPerformanceRank(a: LeaderboardRow, b: LeaderboardRow) {
    const byMacroF1 = compareNullableNumber(a.macroF1, b.macroF1, "desc");
    if (byMacroF1 !== 0) return byMacroF1;
    return a.id.localeCompare(b.id);
  }

  function compareRows(a: LeaderboardRow, b: LeaderboardRow) {
    let comparison = 0;

    if (sortKey === "rank") {
      comparison = compareNullableNumber(a.rank, b.rank, sortDirection);
    } else if (sortKey === "family") {
      comparison = compareString(familyText(a.family), familyText(b.family), sortDirection);
    } else if (sortKey === "macro_f1") {
      comparison = compareNullableNumber(a.macroF1, b.macroF1, sortDirection);
    } else if (sortKey === "net_improvement") {
      comparison = compareNullableNumber(a.netImprovement, b.netImprovement, sortDirection);
    } else {
      comparison = compareNullableNumber(a.modelSizeIndex, b.modelSizeIndex, sortDirection);
    }

    if (comparison !== 0) return comparison;
    return compareNullableNumber(a.rank, b.rank, "asc") || a.name.localeCompare(b.name);
  }

  function compareNullableNumber(
    a: number | null,
    b: number | null,
    direction: SortDirection,
  ) {
    if (a === null && b === null) return 0;
    if (a === null) return 1;
    if (b === null) return -1;
    return direction === "asc" ? a - b : b - a;
  }

  function compareString(a: string, b: string, direction: SortDirection) {
    const comparison = a.localeCompare(b);
    return direction === "asc" ? comparison : -comparison;
  }

  function setSort(nextKey: SortKey) {
    if (sortKey === nextKey) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
      return;
    }

    sortKey = nextKey;
    sortDirection = defaultDirection(nextKey);
  }

  function defaultDirection(nextKey: SortKey): SortDirection {
    if (nextKey === "rank" || nextKey === "family") return "asc";
    return "desc";
  }

  function netImprovementStats(modelId: string) {
    const deltas = catalog.datasets
      .filter((item) => selectedDatasetSet.has(item.id))
      .map((dataset) => {
        const modelScore = averageMetric(
          validResults.filter(
            (result) => result.dataset_id === dataset.id && result.model_id === modelId,
          ),
          "macro_f1",
        );
        const baselineScore = bestClassicalMacroF1(dataset.id);

        if (modelScore === null || baselineScore === null) return null;
        return modelScore - baselineScore;
      })
      .filter((value): value is number => value !== null);

    if (deltas.length === 0) {
      return { mean: null, ci95: null };
    }

    const mean = averageValues(deltas);
    const ci95 =
      deltas.length > 1 ? 1.96 * sampleStandardDeviation(deltas, mean) / Math.sqrt(deltas.length) : 0;

    return { mean, ci95 };
  }

  function bestClassicalMacroF1(datasetId: string) {
    const scores = catalog.models
      .filter((model) => classicalBaselineIds.has(model.id))
      .map((model) =>
        averageMetric(
          validResults.filter(
            (result) => result.dataset_id === datasetId && result.model_id === model.id,
          ),
          "macro_f1",
        ),
      )
      .filter((value): value is number => value !== null);

    if (scores.length === 0) return null;
    return Math.max(...scores);
  }

  function averageValues(values: number[]) {
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }

  function sampleStandardDeviation(values: number[], mean = averageValues(values)) {
    if (values.length < 2) return 0;
    const variance =
      values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1);
    return Math.sqrt(variance);
  }

  function getNetImprovementScale(items: LeaderboardRow[]) {
    const extents = items
      .flatMap((item) => {
        if (item.netImprovement === null) return [];
        const ci = item.netImprovementCi95 ?? 0;
        return [item.netImprovement - ci, item.netImprovement + ci, item.netImprovement];
      })
      .map(Math.abs);

    if (extents.length === 0) return 0.01;
    return Math.max(0.01, ...extents);
  }

  function sortAria(key: SortKey) {
    if (sortKey !== key) return "none";
    return sortDirection === "asc" ? "ascending" : "descending";
  }

  function formatSelectedDatasetSummary() {
    if (selectedDatasetIds.length === catalog.datasets.length) return "All datasets";
    if (selectedDatasetIds.length === 0) return "No datasets";
    if (selectedDatasetIds.length === 1) {
      return (
        catalog.datasets.find((item) => item.id === selectedDatasetIds[0])?.name ??
        "1 dataset"
      );
    }
    return `${selectedDatasetIds.length} datasets`;
  }

  function formatSelectedModelFamilySummary() {
    if (selectedModelFamilyIds.length === modelFamilyOptions.length) return "All architectures";
    if (selectedModelFamilyIds.length === 0) return "No architectures";
    if (selectedModelFamilyIds.length === 1) {
      return formatFamily(selectedModelFamilyIds[0]);
    }
    return `${selectedModelFamilyIds.length} architectures`;
  }

  function formatSelectedModelSummary() {
    if (selectedModelIds.length === catalog.models.length) return "All models";
    if (selectedModelIds.length === 0) return "No models";
    if (selectedModelIds.length === 1) {
      return (
        catalog.models.find((item) => item.id === selectedModelIds[0])?.name ??
        "1 model"
      );
    }
    return `${selectedModelIds.length} models`;
  }

  function isDatasetSelected(id: string) {
    return selectedDatasetSet.has(id);
  }

  function isModelSelected(id: string) {
    return selectedModelSet.has(id);
  }

  function isModelFamilySelected(id: string) {
    return selectedModelFamilySet.has(id);
  }

  function toggleDataset(id: string) {
    if (selectedDatasetSet.has(id)) {
      selectedDatasetIds = selectedDatasetIds.filter((item) => item !== id);
      return;
    }

    selectedDatasetIds = [...selectedDatasetIds, id];
  }

  function toggleModelFamily(id: string) {
    if (selectedModelFamilySet.has(id)) {
      selectedModelFamilyIds = selectedModelFamilyIds.filter((item) => item !== id);
      return;
    }

    selectedModelFamilyIds = [...selectedModelFamilyIds, id];
  }

  function toggleModel(id: string) {
    if (selectedModelSet.has(id)) {
      selectedModelIds = selectedModelIds.filter((item) => item !== id);
      return;
    }

    selectedModelIds = [...selectedModelIds, id];
  }

  function selectAllModelFamilies() {
    selectedModelFamilyIds = modelFamilyOptions.map((item) => item.id);
  }

  function clearModelFamilies() {
    selectedModelFamilyIds = [];
  }

  function selectAllDatasets() {
    selectedDatasetIds = catalog.datasets.map((item) => item.id);
  }

  function clearDatasets() {
    selectedDatasetIds = [];
  }

  function selectAllModels() {
    selectedModelIds = catalog.models.map((item) => item.id);
  }

  function clearModels() {
    selectedModelIds = [];
  }

  function selectTopDatasets() {
    selectedDatasetIds = catalog.datasets.slice(0, 10).map((item) => item.id);
  }

  function selectTopModels() {
    selectedModelIds = catalog.models
      .filter((model) => isFamilyAllowed(model.family))
      .map((model) => ({
        ...model,
        rank: null,
        netImprovement: null,
        netImprovementCi95: null,
        macroF1: averageMetric(
          validResults.filter(
            (result) =>
              result.model_id === model.id && selectedDatasetSet.has(result.dataset_id),
          ),
          "macro_f1",
        ),
        modelSizeMb: null,
        modelSizeIndex: null,
      }))
      .sort(compareByPerformanceRank)
      .slice(0, 10)
      .map((model) => model.id);
  }

  function withModelSizeIndex(baseRows: LeaderboardRow[]) {
    const eligible = baseRows.filter(
      (row) => row.macroF1 !== null && row.modelSizeMb !== null && row.modelSizeMb > 0,
    );

    if (eligible.length === 0) return baseRows;

    const f1Values = eligible.map((row) => row.macroF1 as number);
    const sizeValues = eligible.map((row) => Math.log(row.modelSizeMb as number));
    const minF1 = Math.min(...f1Values);
    const maxF1 = Math.max(...f1Values);
    const minSize = Math.min(...sizeValues);
    const maxSize = Math.max(...sizeValues);

    return baseRows.map((row) => {
      if (row.macroF1 === null || row.modelSizeMb === null || row.modelSizeMb <= 0) {
        return row;
      }

      const f1Norm = normalize(row.macroF1, minF1, maxF1, 1);
      const sizeNorm = normalize(Math.log(row.modelSizeMb), minSize, maxSize, 0);
      const modelSizeIndex =
        1 - Math.sqrt(0.5 * (1 - f1Norm) ** 2 + 0.5 * sizeNorm ** 2);

      return {
        ...row,
        modelSizeIndex,
      };
    });
  }

  function normalize(value: number, min: number, max: number, fallback: number) {
    if (max === min) return fallback;
    return (value - min) / (max - min);
  }

  function formatPercent(score: number | null) {
    if (score === null) return "pending";
    return `${(score * 100).toFixed(1)}%`;
  }

  function formatNetImprovement(score: number | null) {
    if (score === null) return "pending";
    return `${(score * 100).toFixed(2)}%`;
  }

  function formatNetImprovementCi(score: number | null) {
    if (score === null) return "pending";
    return `±${(score * 100).toFixed(2)}%`;
  }

  function netDirection(score: number | null) {
    if (score === null || score === 0) return "flat";
    return score > 0 ? "up" : "down";
  }

  function netBarStyle(row: LeaderboardRow) {
    if (row.netImprovement === null) return "";

    const ci = row.netImprovementCi95 ?? 0;
    const zero = 50;
    const value = netBarPercent(row.netImprovement);
    const ciLow = netBarPercent(row.netImprovement - ci);
    const ciHigh = netBarPercent(row.netImprovement + ci);
    const fillLeft = Math.min(zero, value);
    const fillWidth = Math.abs(value - zero);
    const ciLeft = Math.min(ciLow, ciHigh);
    const ciWidth = Math.abs(ciHigh - ciLow);

    return [
      `--net-fill-left: ${fillLeft.toFixed(2)}%;`,
      `--net-fill-width: ${fillWidth.toFixed(2)}%;`,
      `--net-ci-left: ${ciLeft.toFixed(2)}%;`,
      `--net-ci-width: ${Math.max(ciWidth, 0.8).toFixed(2)}%;`,
      `--net-ci-low: ${ciLow.toFixed(2)}%;`,
      `--net-ci-high: ${ciHigh.toFixed(2)}%;`,
    ].join(" ");
  }

  function netBarPercent(value: number) {
    if (netImprovementScale <= 0) return 50;
    const clamped = Math.max(-netImprovementScale, Math.min(netImprovementScale, value));
    return 50 + (clamped / netImprovementScale) * 50;
  }

  function formatCompactPercent(score: number | null) {
    if (score === null) return "—";
    return `${(score * 100).toFixed(1)}%`;
  }

  function formatMatrixScore(score: number | null) {
    if (score === null) return "—";
    return (score * 100).toFixed(1);
  }

  function formatIndex(score: number | null) {
    if (score === null) return "pending";
    return score.toFixed(3);
  }

  function formatModelSize(size: number | null) {
    if (size === null) return "";
    return `${size < 1 ? size.toFixed(2) : size.toFixed(1)} MB`;
  }

  function getFamilyParts(family: string) {
    return familyPartsById[family] ?? family.split("_").filter(Boolean);
  }

  function isFamilyAllowed(family: string) {
    return getFamilyParts(family).every((part) => selectedModelFamilySet.has(part));
  }

  function familyText(family: string) {
    return getFamilyParts(family).map(formatFamily).join(" ");
  }

  function formatFamily(family: string) {
    const labels: Record<string, string> = {
      attn: "Attention",
      cnn: "CNN",
      dense: "Dense",
      fe: "Features",
      graph: "Graph",
      neural: "Neural",
      rnn: "RNN",
      spec: "Spectral",
    };
    const parts = getFamilyParts(family);

    if (labels[family]) return labels[family];
    if (parts.length > 1) return parts.map(formatFamily).join(" ");
    return family.replaceAll("_", " ");
  }

  function getModelFamilyIds(models: Model[]) {
    return getModelFamilyOptions(models).map((item) => item.id);
  }

  function getModelFamilyOptions(models: Model[]): FilterOption[] {
    const ids = [...new Set(models.flatMap((model) => getFamilyParts(model.family)))];
    return ids
      .sort((a, b) => {
        const aIndex = familyOrder.indexOf(a);
        const bIndex = familyOrder.indexOf(b);
        const aRank = aIndex === -1 ? Number.POSITIVE_INFINITY : aIndex;
        const bRank = bIndex === -1 ? Number.POSITIVE_INFINITY : bIndex;

        if (aRank !== bRank) return aRank - bRank;
        return formatFamily(a).localeCompare(formatFamily(b));
      })
      .map((id) => ({ id, name: formatFamily(id) }));
  }

  function scoreStyle(score: number | null) {
    if (score === null) return "";
    const normalized = Math.max(0, Math.min(1, score));
    const hue =
      normalized < 0.5
        ? interpolate(6, 42, normalized * 2)
        : interpolate(42, 145, (normalized - 0.5) * 2);
    const lightness =
      normalized < 0.5
        ? interpolate(91, 86, normalized * 2)
        : interpolate(86, 76, (normalized - 0.5) * 2);

    return `--score-bg: hsl(${hue} 78% ${lightness}%);`;
  }

  function interpolate(start: number, end: number, amount: number) {
    return start + (end - start) * amount;
  }

  function getModelDetail(id: string) {
    return detailMap[id] ?? null;
  }

  function getDatasetDetail(id: string) {
    return datasetDetailMap[id] ?? null;
  }

  function modelInstitutions(id: string) {
    return getModelDetail(id)?.institutions ?? [];
  }

  function modelInstitutionSummary(id: string) {
    const institutions = modelInstitutions(id);
    if (institutions.length > 3) {
      return [...institutions.slice(0, 2), "et al."];
    }
    return institutions;
  }

  function openModelDetail(id: string) {
    selectedDetailDatasetId = null;
    selectedDetailModelId = id;
  }

  function closeModelDetail() {
    selectedDetailModelId = null;
  }

  function openDatasetDetail(id: string) {
    selectedDetailModelId = null;
    selectedDetailDatasetId = id;
  }

  function closeDatasetDetail() {
    selectedDetailDatasetId = null;
  }

  function closeDetailModal() {
    closeModelDetail();
    closeDatasetDetail();
  }

  function closeSiblingFilterDropdowns(event: Event) {
    const current = event.currentTarget as HTMLDetailsElement | null;
    if (!current?.open) return;

    current
      .closest(".filter-panel")
      ?.querySelectorAll<HTMLDetailsElement>(".dataset-filter details")
      .forEach((details) => {
        if (details !== current) details.open = false;
      });
  }

  function handleModelRowKeydown(event: KeyboardEvent, id: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openModelDetail(id);
    }
  }

  function handleDialogKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      closeDetailModal();
    }
  }

  function formatDetailMetric(value: string | null | undefined) {
    return value ?? "—";
  }

  function formatDatasetMetric(value: number | string | null | undefined) {
    if (typeof value === "number") return numberFormatter.format(value);
    return value ?? "—";
  }

  function getPaperLink(kind: "datasets" | "models", id: string) {
    return linkMap[kind][id] ?? null;
  }

  function hasPaperLink(kind: "datasets" | "models", id: string) {
    return Boolean(getPaperLink(kind, id)?.url);
  }

  function paperUrl(kind: "datasets" | "models", id: string) {
    return getPaperLink(kind, id)?.url ?? "";
  }

  function paperTitle(kind: "datasets" | "models", id: string, fallback: string) {
    return `Open paper: ${getPaperLink(kind, id)?.title ?? fallback}`;
  }

  function datasetInputId(id: string) {
    return `dataset-filter-${id}`;
  }

  function modelFamilyInputId(id: string) {
    return `model-family-filter-${id}`;
  }

  function modelInputId(id: string) {
    return `model-filter-${id}`;
  }

  function createScatterPlot(config: ScatterConfig): ScatterPlot {
    const points = deploymentPoints.flatMap((point) => {
      const metricValue = point[config.metric];

      if (
        typeof metricValue !== "number" ||
        !Number.isFinite(metricValue) ||
        typeof point.mean_test_macro_f1 !== "number" ||
        !Number.isFinite(point.mean_test_macro_f1)
      ) {
        return [];
      }

      return [
        {
          ...point,
          x: metricValue,
          y: point.mean_test_macro_f1,
        },
      ];
    });
    const allMacroF1 = deploymentPoints
      .map((point) => point.mean_test_macro_f1)
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value));

    if (points.length === 0 || allMacroF1.length === 0) {
      return {
        ...config,
        points,
        xMax: 1,
        yMin: 0.45,
        yMax: 0.7,
        xTicks: createLinearTicks(0, 1, 4),
        yTicks: createLinearTicks(0.45, 0.7, 4),
        missingCount: deploymentPoints.length,
      };
    }

    const xMax = niceCostMax(Math.max(...points.map((point) => point.x), 1));
    const yMin = Math.max(0, Math.floor((Math.min(...allMacroF1) - 0.015) * 100) / 100);
    const yMax = Math.min(1, Math.ceil((Math.max(...allMacroF1) + 0.015) * 100) / 100);

    return {
      ...config,
      points,
      xMax,
      yMin,
      yMax,
      xTicks: createLinearTicks(0, xMax, 4),
      yTicks: createLinearTicks(yMin, yMax, 4),
      missingCount: deploymentPoints.length - points.length,
    };
  }

  function createLinearTicks(min: number, max: number, steps: number) {
    if (steps <= 0 || max === min) return [min];
    return Array.from({ length: steps + 1 }, (_, index) => min + ((max - min) * index) / steps);
  }

  function niceCostMax(value: number) {
    if (value <= 2) return Math.ceil(value * 10) / 10;
    if (value <= 10) return Math.ceil(value / 2) * 2;
    if (value <= 30) return Math.ceil(value / 5) * 5;
    return Math.ceil(value / 10) * 10;
  }

  function plotX(value: number, chart: ScatterPlot) {
    const innerWidth = plotBox.width - plotBox.left - plotBox.right;
    return plotBox.left + (value / chart.xMax) * innerWidth;
  }

  function plotY(value: number, chart: ScatterPlot) {
    const innerHeight = plotBox.height - plotBox.top - plotBox.bottom;
    return (
      plotBox.top +
      (1 - normalize(value, chart.yMin, chart.yMax, 0.5)) * innerHeight
    );
  }

  function pointLabelAnchor(point: ScatterPoint, chart: ScatterPlot) {
    return plotX(point.x, chart) > plotBox.width - 112 ? "end" : "start";
  }

  function pointLabelDx(point: ScatterPoint, chart: ScatterPlot) {
    return pointLabelAnchor(point, chart) === "end" ? -8 : 8;
  }

  function isHighlightedScatterPoint(id: string) {
    return highlightedScatterIds.has(id);
  }

  function formatScatterTick(value: number, metric: ScatterMetric) {
    if (metric === "mean_latency_ms") {
      return value >= 10 ? value.toFixed(0) : value.toFixed(1);
    }

    if (metric === "exported_model_size_mb" && value < 1) {
      return value.toFixed(1);
    }

    return value >= 10 ? value.toFixed(0) : value.toFixed(1);
  }

  function formatScatterF1Tick(value: number) {
    return `${(value * 100).toFixed(0)}%`;
  }

  function formatScatterMetricValue(value: number, metric: ScatterMetric) {
    if (metric === "mean_latency_ms") return `${value.toFixed(2)} ms`;
    if (metric === "mean_peak_pss_delta_mb") return `${value.toFixed(2)} MB`;
    return `${value.toFixed(2)} MB`;
  }

  function scatterTitle(point: ScatterPoint, chart: ScatterPlot) {
    return `${point.name}: ${formatPercent(point.y)} Macro-F1, ${formatScatterMetricValue(
      point.x,
      chart.metric,
    )}`;
  }
</script>

<svelte:window onkeydown={handleDialogKeydown} />

<div class="bench-stack">
  <section class="arena-panel filter-panel">
    <div class="panel-header">
      <div>
        <h2>Filters</h2>
      </div>
    </div>

    <div class="filter-content">
      <div class="dataset-filter">
        <span class="filter-label">Datasets</span>
        <details ontoggle={closeSiblingFilterDropdowns}>
          <summary aria-label="Datasets">
            <span>{selectedDatasetSummary}</span>
            <span class="filter-count">
              {selectedDatasetIds.length}/{catalog.datasets.length}
            </span>
          </summary>
          <div class="dataset-menu">
            <div class="dataset-actions" aria-label="Dataset selection actions">
              <button type="button" data-filter-action="all-datasets" onclick={selectAllDatasets}>
                All
              </button>
              <button type="button" data-filter-action="none-datasets" onclick={clearDatasets}>
                None
              </button>
              <button type="button" data-filter-action="top-datasets" onclick={selectTopDatasets}>
                Top 10
              </button>
            </div>
            <div class="dataset-options">
              {#each catalog.datasets as item}
                <div class="dataset-option" data-dataset-id={item.id}>
                  <input
                    id={datasetInputId(item.id)}
                    type="checkbox"
                    value={item.id}
                    checked={isDatasetSelected(item.id)}
                    onchange={() => toggleDataset(item.id)}
                  />
                  <label
                    class="dataset-check"
                    for={datasetInputId(item.id)}
                    aria-label={`Toggle ${item.name}`}
                  ></label>
                  {#if hasPaperLink("datasets", item.id)}
                    <a
                      class="paper-link dataset-option-link"
                      href={paperUrl("datasets", item.id)}
                      title={paperTitle("datasets", item.id, item.name)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {item.name}
                    </a>
                  {:else}
                    <label class="dataset-name-toggle" for={datasetInputId(item.id)}>
                      {item.name}
                    </label>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        </details>
      </div>

      <div class="dataset-filter">
        <span class="filter-label">Models</span>
        <details ontoggle={closeSiblingFilterDropdowns}>
          <summary aria-label="Models">
            <span>{selectedModelSummary}</span>
            <span class="filter-count">
              {selectedModelIds.length}/{catalog.models.length}
            </span>
          </summary>
          <div class="dataset-menu">
            <div class="dataset-actions" aria-label="Model selection actions">
              <button type="button" data-filter-action="all-models" onclick={selectAllModels}>
                All
              </button>
              <button type="button" data-filter-action="none-models" onclick={clearModels}>
                None
              </button>
              <button type="button" data-filter-action="top-models" onclick={selectTopModels}>
                Top 10
              </button>
            </div>
            <div class="dataset-options">
              {#each catalog.models as item}
                <div class="dataset-option" data-model-id={item.id}>
                  <input
                    id={modelInputId(item.id)}
                    type="checkbox"
                    value={item.id}
                    checked={isModelSelected(item.id)}
                    onchange={() => toggleModel(item.id)}
                  />
                  <label
                    class="dataset-check"
                    for={modelInputId(item.id)}
                    aria-label={`Toggle ${item.name}`}
                  ></label>
                  {#if hasPaperLink("models", item.id)}
                    <a
                      class="paper-link dataset-option-link"
                      href={paperUrl("models", item.id)}
                      title={paperTitle("models", item.id, item.name)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {item.name}
                    </a>
                  {:else}
                    <label class="dataset-name-toggle" for={modelInputId(item.id)}>
                      {item.name}
                    </label>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        </details>
      </div>

      <div class="dataset-filter">
        <span class="filter-label">Architecture</span>
        <details ontoggle={closeSiblingFilterDropdowns}>
          <summary aria-label="Architecture">
            <span>{selectedModelFamilySummary}</span>
            <span class="filter-count">
              {selectedModelFamilyIds.length}/{modelFamilyOptions.length}
            </span>
          </summary>
          <div class="dataset-menu">
            <div class="dataset-actions" aria-label="Architecture selection actions">
              <button type="button" onclick={selectAllModelFamilies}>All</button>
              <button type="button" onclick={clearModelFamilies}>None</button>
            </div>
            <div class="dataset-options">
              {#each modelFamilyOptions as item}
                <div class="dataset-option" data-model-family-id={item.id}>
                  <input
                    id={modelFamilyInputId(item.id)}
                    type="checkbox"
                    value={item.id}
                    checked={isModelFamilySelected(item.id)}
                    onchange={() => toggleModelFamily(item.id)}
                  />
                  <label
                    class="dataset-check"
                    for={modelFamilyInputId(item.id)}
                    aria-label={`Toggle ${item.name}`}
                  ></label>
                  <label class="dataset-name-toggle" for={modelFamilyInputId(item.id)}>
                    <span class="family-pill">{item.name}</span>
                  </label>
                </div>
              {/each}
            </div>
          </div>
        </details>
      </div>
    </div>
  </section>

  <section class="arena-panel">
    <div class="panel-header">
      <div>
        <h2>Leaderboard</h2>
      </div>
    </div>

    <div class="table-wrap leaderboard-wrap">
      <table class="leaderboard-table">
        <thead>
          <tr>
            <th aria-sort={sortAria("rank")}>
              <span class="metric-heading">
                <button
                  type="button"
                  class:active-sort={sortKey === "rank"}
                  class="sort-button"
                  onclick={() => setSort("rank")}
                >
                  Rank
                  <span class="sort-glyph" aria-hidden="true">
                    <span class:active-arrow={sortKey === "rank" && sortDirection === "asc"}></span>
                    <span class:active-arrow={sortKey === "rank" && sortDirection === "desc"}></span>
                  </span>
                </button>
                <span
                  class="info-tip"
                  tabindex="0"
                  title={metricInfo.rank}
                  aria-label={metricInfo.rank}
                  data-tip={metricInfo.rank}
                >
                  i
                </span>
              </span>
            </th>
            <th>Model</th>
            <th aria-sort={sortAria("net_improvement")}>
              <span class="metric-heading">
                <button
                  type="button"
                  class:active-sort={sortKey === "net_improvement"}
                  class="sort-button"
                  onclick={() => setSort("net_improvement")}
                >
                  Net Improvement
                  <span class="sort-glyph" aria-hidden="true">
                    <span
                      class:active-arrow={sortKey === "net_improvement" && sortDirection === "asc"}
                    ></span>
                    <span
                      class:active-arrow={sortKey === "net_improvement" && sortDirection === "desc"}
                    ></span>
                  </span>
                </button>
                <span
                  class="info-tip"
                  tabindex="0"
                  title={metricInfo.netImprovement}
                  aria-label={metricInfo.netImprovement}
                  data-tip={metricInfo.netImprovement}
                >
                  i
                </span>
              </span>
            </th>
            <th aria-sort={sortAria("family")}>
              <button
                type="button"
                class:active-sort={sortKey === "family"}
                class="sort-button"
                onclick={() => setSort("family")}
              >
                Architecture
                <span class="sort-glyph" aria-hidden="true">
                  <span class:active-arrow={sortKey === "family" && sortDirection === "asc"}></span>
                  <span class:active-arrow={sortKey === "family" && sortDirection === "desc"}></span>
                </span>
              </button>
            </th>
            <th aria-sort={sortAria("macro_f1")}>
              <span class="metric-heading">
                <button
                  type="button"
                  class:active-sort={sortKey === "macro_f1"}
                  class="sort-button"
                  onclick={() => setSort("macro_f1")}
                >
                  <span class="mean-metric-icon" aria-hidden="true"></span>
                  Macro F1
                  <span class="sort-glyph" aria-hidden="true">
                    <span class:active-arrow={sortKey === "macro_f1" && sortDirection === "asc"}></span>
                    <span class:active-arrow={sortKey === "macro_f1" && sortDirection === "desc"}></span>
                  </span>
                </button>
                <span
                  class="info-tip"
                  tabindex="0"
                  title={metricInfo.macroF1}
                  aria-label={metricInfo.macroF1}
                  data-tip={metricInfo.macroF1}
                >
                  i
                </span>
              </span>
            </th>
            <th aria-sort={sortAria("model_size")}>
              <span class="metric-heading">
                <button
                  type="button"
                  class:active-sort={sortKey === "model_size"}
                  class="sort-button"
                  onclick={() => setSort("model_size")}
                >
                  Efficiency Score
                  <span class="sort-glyph" aria-hidden="true">
                    <span class:active-arrow={sortKey === "model_size" && sortDirection === "asc"}></span>
                    <span class:active-arrow={sortKey === "model_size" && sortDirection === "desc"}></span>
                  </span>
                </button>
                <span
                  class="info-tip"
                  tabindex="0"
                  title={metricInfo.modelSize}
                  aria-label={metricInfo.modelSize}
                  data-tip={metricInfo.modelSize}
                >
                  i
                </span>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {#each rows as row}
            <tr
              class="clickable-row"
              role="button"
              tabindex="0"
              aria-label={`Open model details: ${row.name}`}
              onclick={() => openModelDetail(row.id)}
              onkeydown={(event) => handleModelRowKeydown(event, row.id)}
            >
              <td class="rank">{row.rank ?? "—"}</td>
              <td class="model-cell">
                <span class="model-title-button">
                  {row.name}
                </span>
                <span class="institution-list">
                  {#each modelInstitutionSummary(row.id) as institution, index}
                    <span>{institution}{index < modelInstitutionSummary(row.id).length - 1 ? " · " : ""}</span>
                  {:else}
                    <span>Institution metadata pending</span>
                  {/each}
                </span>
              </td>
              <td class="net-cell" class:negative-score={netDirection(row.netImprovement) === "down"}>
                {#if row.netImprovement === null}
                  <span class="pending">pending</span>
                {:else}
                  <div class="net-visual" style={netBarStyle(row)}>
                    <div class="net-score">
                      <strong>
                        <span
                          class="net-direction"
                          class:down={netDirection(row.netImprovement) === "down"}
                          class:flat={netDirection(row.netImprovement) === "flat"}
                          aria-hidden="true"
                        ></span>
                        {formatNetImprovement(row.netImprovement)}
                      </strong>
                      <span>{formatNetImprovementCi(row.netImprovementCi95)}</span>
                    </div>
                    <div class="net-bar" aria-hidden="true">
                      <span class="net-fill"></span>
                      <span class="net-zero"></span>
                      <span class="net-ci-line"></span>
                      <span class="net-ci-cap net-ci-low"></span>
                      <span class="net-ci-cap net-ci-high"></span>
                    </div>
                  </div>
                {/if}
              </td>
              <td class="family">
                <div class="family-pill-list" aria-label={`Architecture: ${familyText(row.family)}`}>
                  {#each getFamilyParts(row.family) as familyPart}
                    <span class="family-pill">{formatFamily(familyPart)}</span>
                  {/each}
                </div>
              </td>
              <td class="number">{formatPercent(row.macroF1)}</td>
              <td class="number">
                {#if row.modelSizeIndex === null}
                  <span class="pending">pending</span>
                {:else}
                  <strong>{formatIndex(row.modelSizeIndex)}</strong>
                  {#if row.modelSizeMb !== null}
                    <span>{formatModelSize(row.modelSizeMb)}</span>
                  {/if}
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="arena-panel matrix-panel">
    <div class="panel-header">
      <div>
        <h2>Dataset × Model Matrix</h2>
      </div>
    </div>

    <div class="table-wrap matrix-wrap">
      <table class="matrix-table">
        <thead>
          <tr>
            <th class="sticky-col">Dataset</th>
            {#each visibleModels as model}
              <th
                class="matrix-model-heading"
                title={`Open model details: ${model.name}`}
                onclick={() => openModelDetail(model.id)}
              >
                <span>
                  <button
                    class="matrix-model-button"
                    type="button"
                    onclick={() => openModelDetail(model.id)}
                  >
                    {model.name}
                  </button>
                </span>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each matrixRows as row}
            <tr>
              <th class="sticky-col dataset-cell" title={`${row.name} · ${row.id}`}>
                <button
                  class="dataset-title-button"
                  type="button"
                  title={`Open dataset details: ${row.name}`}
                  onclick={() => openDatasetDetail(row.id)}
                >
                  {row.name}
                </button>
              </th>
              {#each row.cells as cell}
                <td
                  class:pending-cell={cell.macroF1 === null}
                  style={scoreStyle(cell.macroF1)}
                  title={`${row.name} · ${cell.modelId}: ${formatPercent(cell.macroF1)}`}
                >
                  <strong>{formatMatrixScore(cell.macroF1)}</strong>
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  {#if deploymentTradeoffs && deploymentPoints.length > 0}
    <section class="arena-panel scatter-panel">
      <div class="panel-header">
        <div>
          <h2>Deployment Trade-Offs</h2>
        </div>
      </div>

      <div class="scatter-grid">
        {#each scatterPlots as chart}
          <article class="scatter-plot">
            <h3>{chart.title}</h3>
            <svg
              class="scatter-chart"
              viewBox={`0 0 ${plotBox.width} ${plotBox.height}`}
              role="img"
              aria-label={chart.title}
            >
              <g class="scatter-grid-lines" aria-hidden="true">
                {#each chart.yTicks as tick}
                  <line
                    x1={plotBox.left}
                    x2={plotBox.width - plotBox.right}
                    y1={plotY(tick, chart)}
                    y2={plotY(tick, chart)}
                  ></line>
                {/each}
              </g>
              <g class="scatter-axis">
                <line
                  x1={plotBox.left}
                  x2={plotBox.left}
                  y1={plotBox.top}
                  y2={plotBox.height - plotBox.bottom}
                ></line>
                <line
                  x1={plotBox.left}
                  x2={plotBox.width - plotBox.right}
                  y1={plotBox.height - plotBox.bottom}
                  y2={plotBox.height - plotBox.bottom}
                ></line>
              </g>
              <g class="scatter-ticks">
                {#each chart.xTicks as tick}
                  <g>
                    <line
                      x1={plotX(tick, chart)}
                      x2={plotX(tick, chart)}
                      y1={plotBox.height - plotBox.bottom}
                      y2={plotBox.height - plotBox.bottom + 5}
                    ></line>
                    <text
                      x={plotX(tick, chart)}
                      y={plotBox.height - plotBox.bottom + 20}
                      text-anchor="middle"
                    >
                      {formatScatterTick(tick, chart.metric)}
                    </text>
                  </g>
                {/each}
                {#each chart.yTicks as tick}
                  <g>
                    <line
                      x1={plotBox.left - 5}
                      x2={plotBox.left}
                      y1={plotY(tick, chart)}
                      y2={plotY(tick, chart)}
                    ></line>
                    <text
                      x={plotBox.left - 9}
                      y={plotY(tick, chart)}
                      dominant-baseline="middle"
                      text-anchor="end"
                    >
                      {formatScatterF1Tick(tick)}
                    </text>
                  </g>
                {/each}
              </g>
              <text
                class="scatter-axis-title"
                x={(plotBox.left + plotBox.width - plotBox.right) / 2}
                y={plotBox.height - 8}
                text-anchor="middle"
              >
                {chart.xLabel}
              </text>
              <text
                class="scatter-axis-title"
                dominant-baseline="middle"
                text-anchor="middle"
                transform={`translate(14 ${(plotBox.top + plotBox.height - plotBox.bottom) / 2}) rotate(-90)`}
              >
                Mean test Macro-F1
              </text>
              <g class="scatter-points">
                {#each chart.points as point}
                  <g class="scatter-point">
                    <title>{scatterTitle(point, chart)}</title>
                    <circle
                      cx={plotX(point.x, chart)}
                      cy={plotY(point.y, chart)}
                      r={5.4}
                      fill={point.color}
                    ></circle>
                    {#if isHighlightedScatterPoint(point.model_id)}
                      <text
                        class="scatter-point-label"
                        x={plotX(point.x, chart)}
                        y={plotY(point.y, chart) - 7}
                        dx={pointLabelDx(point, chart)}
                        text-anchor={pointLabelAnchor(point, chart)}
                      >
                        {point.name}
                      </text>
                    {/if}
                  </g>
                {/each}
              </g>
            </svg>
          </article>
        {/each}
      </div>

      {#if missingModelSizeNames}
        <p class="scatter-note">
          {missingModelSizeNames} is omitted from the exported model-size panel because
          the static export does not include an exported-size value for that model.
        </p>
      {/if}
    </section>
  {/if}

  {#if selectedDetailModel && selectedDetail}
    <div class="modal-layer" role="presentation">
      <button
        class="modal-backdrop"
        type="button"
        aria-label="Close model details"
        onclick={closeModelDetail}
      ></button>
      <section
        class="model-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="model-detail-title"
      >
        <div class="model-modal-header">
          <div>
            <h2 id="model-detail-title">{selectedDetailModel.name}</h2>
            <p>{getPaperLink("models", selectedDetailModel.id)?.title ?? selectedDetailModel.name}</p>
          </div>
          <button
            class="modal-close"
            type="button"
            aria-label="Close model details"
            onclick={closeModelDetail}
          ></button>
        </div>

        <div class="detail-metrics" aria-label="Model size and compute">
          <div>
            <span>Params</span>
            <strong>{formatDetailMetric(selectedDetail.params)}</strong>
          </div>
          <div>
            <span>FLOPs</span>
            <strong>{formatDetailMetric(selectedDetail.flops)}</strong>
          </div>
        </div>

        <div class="detail-info-card">
          <strong>Table 2 setup</strong>
          <p>
            These counts are reported for 6 sensors, 5 classes, and 128
            timesteps.
          </p>
        </div>

        <div class="detail-section">
          <h3>Paper</h3>
          {#if hasPaperLink("models", selectedDetailModel.id)}
            <a
              class="paper-link detail-paper-link"
              href={paperUrl("models", selectedDetailModel.id)}
              title={paperTitle("models", selectedDetailModel.id, selectedDetailModel.name)}
              target="_blank"
              rel="noreferrer"
            >
              Open paper PDF
            </a>
          {:else}
            <p class="pending">Paper link pending</p>
          {/if}
        </div>

        <div class="detail-section">
          <h3>Authors And Affiliations</h3>
          <ul class="author-list">
            {#each selectedDetail.authors as author}
              <li>
                <strong>{author.name}</strong>
                <span>{author.affiliation}</span>
              </li>
            {/each}
          </ul>
        </div>
      </section>
    </div>
  {/if}

  {#if selectedDetailDataset && selectedDatasetDetail}
    <div class="modal-layer" role="presentation">
      <button
        class="modal-backdrop"
        type="button"
        aria-label="Close dataset details"
        onclick={closeDatasetDetail}
      ></button>
      <section
        class="model-modal dataset-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dataset-detail-title"
      >
        <div class="model-modal-header">
          <div>
            <h2 id="dataset-detail-title">{selectedDetailDataset.name}</h2>
            <p>
              {getPaperLink("datasets", selectedDetailDataset.id)?.title ??
                selectedDetailDataset.name}
            </p>
          </div>
          <button
            class="modal-close"
            type="button"
            aria-label="Close dataset details"
            onclick={closeDatasetDetail}
          ></button>
        </div>

        <div class="detail-metrics dataset-detail-metrics" aria-label="Dataset statistics">
          <div>
            <span>Year</span>
            <strong>{selectedDatasetDetail.year}</strong>
          </div>
          <div>
            <span>Citations</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.citations)}</strong>
          </div>
          <div>
            <span>Subjects</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.subjects)}</strong>
          </div>
          <div>
            <span>Activities</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.activities)}</strong>
          </div>
          <div>
            <span>Channels</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.channels)}</strong>
          </div>
          <div>
            <span>Settings</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.settings)}</strong>
          </div>
          <div>
            <span>Device Types</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.deviceTypes)}</strong>
          </div>
          <div>
            <span>Sensor Modalities</span>
            <strong>{formatDatasetMetric(selectedDatasetDetail.sensorModalities)}</strong>
          </div>
        </div>

        <div class="detail-info-card">
          <strong>{datasetDetails.source.table} stats</strong>
          <p>
            {datasetDetails.source.note} Abbreviations follow the paper:
            {datasetDetails.source.abbreviations}
          </p>
        </div>

        <div class="detail-section">
          <h3>Paper</h3>
          {#if hasPaperLink("datasets", selectedDetailDataset.id)}
            <a
              class="paper-link detail-paper-link"
              href={paperUrl("datasets", selectedDetailDataset.id)}
              title={paperTitle("datasets", selectedDetailDataset.id, selectedDetailDataset.name)}
              target="_blank"
              rel="noreferrer"
            >
              Open dataset paper PDF
            </a>
          {:else}
            <p class="pending">Paper link pending</p>
          {/if}
        </div>
      </section>
    </div>
  {/if}
</div>

<style>
  .bench-stack {
    display: grid;
    gap: 14px;
    min-width: 0;
  }

  .arena-panel {
    min-width: 0;
    border: 1px solid lightgray;
    border-radius: 8px;
    background: var(--panel);
    overflow: hidden;
    box-shadow: none;
  }

  .filter-panel {
    position: relative;
    z-index: 20;
    overflow: visible;
  }

  .arena-panel.filter-panel {
    overflow: visible;
  }

  .filter-panel > .panel-header {
    border-radius: 7px 7px 0 0;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: center;
    min-height: 65px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--line);
    background: var(--panel-soft);
  }

  h2,
  p {
    margin: 0;
  }

  h2 {
    font-family: var(--display-serif);
    font-size: 1.3rem;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1.05;
  }

  p,
  span {
    color: var(--muted);
  }

  th {
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .filter-content {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    padding: 14px 16px 16px;
  }

  .filter-label {
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .dataset-filter {
    position: relative;
    display: grid;
    gap: 6px;
    min-width: 0;
    width: 100%;
  }

  .dataset-filter details {
    position: relative;
  }

  .dataset-filter summary {
    display: flex;
    min-height: 36px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    background: var(--panel-soft);
    color: var(--ink);
    padding: 0 10px;
    cursor: pointer;
    list-style: none;
  }

  .dataset-filter summary::-webkit-details-marker {
    display: none;
  }

  .dataset-filter summary::after {
    content: "";
    width: 7px;
    height: 7px;
    border-right: 1.5px solid var(--muted);
    border-bottom: 1.5px solid var(--muted);
    transform: rotate(45deg) translateY(-2px);
  }

  .dataset-filter details[open] summary::after {
    transform: rotate(225deg) translateY(-1px);
  }

  .dataset-filter summary span:first-child {
    overflow: hidden;
    color: var(--ink);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dataset-filter summary:focus-visible {
    outline: 2px solid hsl(24 6% 17% / 0.28);
    outline-offset: 2px;
  }

  .dataset-filter summary:hover {
    border-color: var(--accent);
    background: var(--panel);
  }

  .filter-count {
    margin-left: auto;
    color: var(--muted);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.74rem;
  }

  .dataset-menu {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    z-index: 10;
    width: min(360px, calc(100vw - 48px));
    max-height: min(560px, 72vh);
    overflow: auto;
    border: 1px solid lightgray;
    border-radius: 8px;
    background: var(--panel);
    box-shadow: none;
  }

  .dataset-actions {
    position: sticky;
    top: 0;
    z-index: 1;
    display: flex;
    gap: 8px;
    padding: 8px;
    border-bottom: 1px solid var(--line);
    background: var(--panel-soft);
  }

  .dataset-actions button {
    min-height: 28px;
    border: 1px solid var(--line-strong);
    border-radius: 7px;
    background: var(--panel);
    color: var(--muted-strong);
    padding: 0 10px;
    cursor: pointer;
  }

  .dataset-actions button:hover {
    border-color: var(--accent);
    color: var(--ink);
  }

  .paper-link {
    color: inherit;
    text-decoration: underline;
    text-decoration-color: hsl(24 6% 17% / 0.3);
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
  }

  .paper-link:hover,
  .paper-link:focus-visible {
    color: inherit;
    text-decoration-color: currentColor;
  }

  .dataset-cell .paper-link,
  .dataset-title-button {
    color: var(--ink);
  }

  .dataset-option-link,
  .dataset-name-toggle {
    overflow: hidden;
    color: var(--muted-strong);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dataset-name-toggle {
    cursor: pointer;
  }

  .dataset-options {
    display: grid;
    padding: 4px 0;
  }

  .dataset-option {
    display: grid;
    grid-template-columns: 18px minmax(0, 1fr);
    gap: 9px;
    align-items: center;
    min-height: 30px;
    padding: 0 10px;
    color: var(--muted-strong);
  }

  .dataset-option:hover {
    background: var(--panel-soft);
  }

  .dataset-option input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }

  .dataset-check {
    display: grid;
    width: 16px;
    height: 16px;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 4px;
    background: var(--panel);
  }

  .dataset-check::after {
    content: "";
    width: 7px;
    height: 4px;
    border-bottom: 2px solid var(--panel);
    border-left: 2px solid var(--panel);
    opacity: 0;
    transform: rotate(-45deg) translateY(-1px);
  }

  .dataset-option input:checked + .dataset-check {
    border-color: var(--accent-strong);
    background: var(--accent);
  }

  .dataset-option input:checked + .dataset-check::after {
    opacity: 1;
  }

  .dataset-option input:focus-visible + .dataset-check {
    outline: 2px solid hsl(24 6% 17% / 0.28);
    outline-offset: 2px;
  }

  .table-wrap {
    min-width: 0;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    border-bottom: 1px solid var(--line);
    text-align: left;
    vertical-align: middle;
  }

  .leaderboard-table {
    min-width: 1240px;
  }

  .leaderboard-table th,
  .leaderboard-table td {
    padding: 12px 16px;
  }

  .leaderboard-table th:nth-child(3),
  .leaderboard-table td:nth-child(3) {
    width: 330px;
  }

  .leaderboard-table tbody tr.clickable-row {
    cursor: pointer;
  }

  .leaderboard-table tbody tr:hover td {
    background: hsl(33 31% 94% / 0.72);
  }

  .leaderboard-table tbody tr.clickable-row:focus-visible {
    outline: 2px solid hsl(24 6% 17% / 0.3);
    outline-offset: -2px;
  }

  .leaderboard-table tbody tr.clickable-row:focus-visible td {
    background: hsl(33 31% 94% / 0.72);
  }

  .sort-button {
    appearance: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    border: 0;
    background: transparent;
    color: inherit;
    padding: 0;
    font: inherit;
    text-align: left;
    text-transform: inherit;
    cursor: pointer;
  }

  .metric-heading {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .mean-metric-icon {
    position: relative;
    display: inline-block;
    width: 13px;
    height: 13px;
    flex: 0 0 auto;
    border: 1.35px solid currentColor;
    border-radius: 50%;
    color: currentColor;
    transform: translateY(-0.5px);
  }

  .mean-metric-icon::before {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 15px;
    height: 1.35px;
    background: currentColor;
    content: "";
    transform: translate(-50%, -50%) rotate(-42deg);
  }

  .info-tip {
    position: relative;
    display: inline-grid;
    width: 15px;
    height: 15px;
    place-items: center;
    border: 1px solid hsl(24 6% 17% / 0.34);
    border-radius: 50%;
    color: var(--muted-strong);
    cursor: help;
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.62rem;
    font-weight: 600;
    line-height: 1;
    text-transform: none;
  }

  .info-tip::after {
    position: absolute;
    top: calc(100% + 8px);
    left: 50%;
    z-index: 30;
    width: 248px;
    max-width: min(248px, 70vw);
    padding: 8px 10px;
    border: 1px solid lightgray;
    border-radius: 7px;
    background: var(--ink);
    color: var(--panel);
    box-shadow: none;
    content: attr(data-tip);
    font-family:
      "baselGrotesk", "Inter", ui-sans-serif, system-ui, -apple-system,
      BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.74rem;
    font-weight: 500;
    line-height: 1.35;
    opacity: 0;
    pointer-events: none;
    text-align: left;
    text-transform: none;
    transform: translate(-50%, -2px);
    transition:
      opacity 120ms ease,
      transform 120ms ease;
    white-space: normal;
  }

  .info-tip::before {
    position: absolute;
    top: calc(100% + 4px);
    left: 50%;
    z-index: 31;
    width: 8px;
    height: 8px;
    background: var(--ink);
    content: "";
    opacity: 0;
    pointer-events: none;
    transform: translateX(-50%) rotate(45deg);
    transition: opacity 120ms ease;
  }

  .info-tip:hover::after,
  .info-tip:focus-visible::after,
  .info-tip:hover::before,
  .info-tip:focus-visible::before {
    opacity: 1;
    transform: translate(-50%, 0);
  }

  .info-tip:hover::before,
  .info-tip:focus-visible::before {
    transform: translateX(-50%) rotate(45deg);
  }

  .sort-button.active-sort {
    color: var(--ink);
  }

  .sort-glyph {
    display: inline-grid;
    gap: 2px;
    width: 8px;
    min-width: 8px;
    color: hsl(24 6% 17% / 0.16);
    justify-items: center;
  }

  .sort-glyph span {
    display: block;
    width: 0;
    height: 0;
    min-width: 0;
    border-right: 3.5px solid transparent;
    border-left: 3.5px solid transparent;
    opacity: 1;
    transition:
      border-color 120ms ease,
      opacity 120ms ease;
  }

  .sort-glyph span:first-child {
    border-bottom: 4px solid currentColor;
  }

  .sort-glyph span:last-child {
    border-top: 4px solid currentColor;
  }

  .sort-glyph span.active-arrow {
    opacity: 1;
    color: var(--ink);
  }

  .sort-button.active-sort .sort-glyph span:not(.active-arrow) {
    color: hsl(24 6% 17% / 0.18);
    opacity: 0.72;
  }

  .sort-button:not(.active-sort) .sort-glyph span {
    color: hsl(24 6% 17% / 0.12);
    opacity: 0.62;
  }

  .sort-button:hover .sort-glyph span,
  .sort-button:focus-visible .sort-glyph span {
    color: hsl(24 6% 17% / 0.32);
    opacity: 1;
  }

  .sort-button.active-sort:hover .sort-glyph span.active-arrow,
  .sort-button.active-sort:focus-visible .sort-glyph span.active-arrow {
    color: var(--ink);
  }

  .rank,
  .number,
  .net-cell {
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .rank {
    color: var(--muted-strong);
    width: 68px;
  }

  .number strong,
  .number span {
    display: block;
  }

  .number strong {
    color: var(--ink);
    font-size: 0.94rem;
    font-weight: 500;
  }

  .number span {
    font-size: 0.78rem;
  }

  .model-title-button {
    display: block;
    color: var(--ink);
    font-size: 0.94rem;
    font-weight: 500;
    line-height: 1.2;
    text-decoration: underline;
    text-decoration-color: hsl(24 6% 17% / 0.5);
    text-decoration-style: dotted;
    text-decoration-thickness: 1px;
    text-underline-offset: 4px;
  }

  .clickable-row:hover .model-title-button,
  .clickable-row:focus-visible .model-title-button {
    text-decoration-color: currentColor;
    text-decoration-style: solid;
  }

  .institution-list {
    display: block;
    max-width: 260px;
    margin-top: 4px;
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.25;
  }

  .institution-list span {
    color: inherit;
  }

  .net-visual {
    display: grid;
    grid-template-columns: 74px minmax(150px, 1fr);
    gap: 14px;
    align-items: center;
  }

  .net-score strong,
  .net-score span {
    display: block;
  }

  .net-score strong {
    display: flex;
    align-items: center;
    gap: 4px;
    color: hsl(125 49% 33%);
    font-size: 0.94rem;
    font-weight: 500;
    line-height: 1.1;
  }

  .net-score span {
    margin-top: 2px;
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.1;
  }

  .net-cell.negative-score .net-score strong {
    color: hsl(2 63% 45%);
  }

  .net-direction {
    width: 0;
    height: 0;
    border-right: 3.5px solid transparent;
    border-bottom: 5px solid currentColor;
    border-left: 3.5px solid transparent;
    color: inherit;
  }

  .net-direction.down {
    border-top: 5px solid currentColor;
    border-bottom: 0;
  }

  .net-direction.flat {
    width: 7px;
    height: 2px;
    border: 0;
    background: currentColor;
  }

  .net-bar {
    position: relative;
    height: 16px;
    background: hsl(33 31% 94%);
    overflow: visible;
  }

  .net-fill {
    position: absolute;
    top: 0;
    left: var(--net-fill-left, 50%);
    width: var(--net-fill-width, 0%);
    height: 100%;
    background: hsl(125 49% 43%);
  }

  .net-cell.negative-score .net-fill {
    background: hsl(2 63% 54%);
  }

  .net-zero {
    position: absolute;
    top: -2px;
    bottom: -2px;
    left: 50%;
    width: 1px;
    background: hsl(24 6% 17% / 0.34);
  }

  .net-ci-line {
    position: absolute;
    top: 50%;
    left: var(--net-ci-left, 50%);
    width: var(--net-ci-width, 0%);
    height: 1.5px;
    background: hsl(24 6% 17% / 0.55);
    transform: translateY(-50%);
  }

  .net-ci-cap {
    position: absolute;
    top: 3px;
    width: 1.5px;
    height: 10px;
    background: hsl(24 6% 17% / 0.55);
    transform: translateX(-50%);
  }

  .net-ci-low {
    left: var(--net-ci-low, 50%);
  }

  .net-ci-high {
    left: var(--net-ci-high, 50%);
  }

  .family {
    color: var(--muted-strong);
  }

  .family-pill-list {
    display: grid;
    grid-template-columns: repeat(2, max-content);
    gap: 5px 6px;
    align-items: center;
  }

  .family-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 20px;
    max-width: 5.8rem;
    border: 1px solid lightgray;
    border-radius: 999px;
    background: var(--panel-soft);
    color: var(--ink);
    padding: 3px 8px;
    font-size: 0.7rem;
    font-weight: 600;
    line-height: 1.05;
    overflow-wrap: anywhere;
    text-align: center;
    white-space: normal;
  }

  .dataset-name-toggle .family-pill {
    min-height: 18px;
    font-size: 0.68rem;
  }

  .pending {
    color: var(--muted);
  }

  .matrix-wrap {
    max-height: none;
    overflow: visible;
  }

  .matrix-table {
    width: 100%;
    min-width: 0;
    margin: 0;
    table-layout: fixed;
  }

  .matrix-table th,
  .matrix-table td {
    height: 30px;
    padding: 0 4px;
    border-right: 1px solid var(--line);
    text-align: center;
  }

  .matrix-table thead th {
    background: var(--panel-strong);
  }

  .matrix-table thead th:not(.sticky-col) {
    height: 148px;
    vertical-align: middle;
  }

  .matrix-model-heading {
    cursor: pointer;
  }

  .matrix-table thead th span {
    display: inline-block;
    max-height: 132px;
    color: var(--muted-strong);
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.15;
    text-transform: none;
    white-space: nowrap;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
  }

  .matrix-model-button {
    border: 0;
    background: transparent;
    color: inherit;
    padding: 0;
    font: inherit;
    text-align: inherit;
    text-decoration: underline;
    text-decoration-color: hsl(24 6% 17% / 0.5);
    text-decoration-style: dotted;
    text-decoration-thickness: 1px;
    text-underline-offset: 4px;
    cursor: pointer;
  }

  .matrix-model-heading:hover .matrix-model-button,
  .matrix-model-button:hover,
  .matrix-model-button:focus-visible {
    color: var(--ink);
    text-decoration-color: currentColor;
    text-decoration-style: solid;
  }

  .matrix-model-button:focus-visible {
    outline: 2px solid hsl(24 6% 17% / 0.28);
    outline-offset: 3px;
  }

  .matrix-table td {
    background: var(--score-bg, transparent);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .matrix-table td strong,
  .matrix-table td span,
  .dataset-title-button,
  .dataset-cell .paper-link,
  .dataset-cell span {
    display: block;
  }

  .matrix-table td strong {
    color: var(--ink);
    font-size: 0.94rem;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 30px;
  }

  .matrix-table td span,
  .dataset-cell span {
    font-size: 0.72rem;
  }

  .matrix-table .pending-cell {
    background: hsl(33 31% 94% / 0.72);
  }

  .matrix-table .pending-cell strong {
    color: var(--muted);
  }

  .sticky-col {
    width: 204px !important;
    min-width: 204px !important;
    background: var(--panel-strong);
  }

  .dataset-cell {
    height: 30px;
    padding: 0 12px !important;
    overflow: hidden;
    text-align: left !important;
    text-transform: none;
    white-space: nowrap;
  }

  .dataset-title-button {
    width: 100%;
    border: 0;
    background: transparent;
    color: var(--ink);
    overflow: hidden;
    padding: 0;
    font-size: 0.94rem;
    font-weight: 500;
    font-family: inherit;
    line-height: 30px;
    text-align: left;
    text-decoration: underline;
    text-decoration-color: hsl(24 6% 17% / 0.5);
    text-decoration-style: dotted;
    text-decoration-thickness: 1px;
    text-underline-offset: 4px;
    text-overflow: ellipsis;
    text-transform: none;
    white-space: nowrap;
    cursor: pointer;
  }

  .dataset-cell:hover .dataset-title-button,
  .dataset-title-button:hover,
  .dataset-title-button:focus-visible {
    text-decoration-color: currentColor;
    text-decoration-style: solid;
  }

  .dataset-title-button:focus-visible {
    outline: 2px solid hsl(24 6% 17% / 0.28);
    outline-offset: -2px;
  }

  .scatter-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    padding: 16px;
  }

  .scatter-plot {
    display: grid;
    min-width: 0;
    gap: 8px;
    align-content: start;
  }

  .scatter-plot h3 {
    margin: 0;
    color: var(--ink);
    font-family: var(--display-serif);
    font-size: 1rem;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1.15;
  }

  .scatter-chart {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }

  .scatter-grid-lines line {
    stroke: hsl(24 6% 17% / 0.1);
    stroke-width: 1;
  }

  .scatter-axis line {
    stroke: var(--ink);
    stroke-width: 1.15;
  }

  .scatter-ticks line {
    stroke: hsl(24 6% 17% / 0.4);
    stroke-width: 1;
  }

  .scatter-ticks text,
  .scatter-axis-title {
    fill: var(--muted-strong);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 9px;
    font-weight: 500;
  }

  .scatter-axis-title {
    fill: var(--ink);
    font-size: 9.4px;
  }

  .scatter-point circle {
    stroke: var(--panel);
    stroke-width: 1.6;
  }

  .scatter-point:hover circle {
    stroke: var(--ink);
    stroke-width: 2;
  }

  .scatter-point-label {
    fill: var(--ink);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0;
    paint-order: stroke;
    stroke: var(--panel);
    stroke-linejoin: round;
    stroke-width: 3px;
  }

  .scatter-note {
    padding: 0 16px 16px;
    color: var(--muted-strong);
    font-size: 0.82rem;
    line-height: 1.35;
  }

  .modal-layer {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: grid;
    place-items: center;
    padding: 24px;
  }

  .modal-backdrop {
    position: absolute;
    inset: 0;
    border: 0;
    background: hsl(24 6% 17% / 0.28);
    cursor: pointer;
  }

  .model-modal {
    position: relative;
    z-index: 1;
    display: grid;
    gap: 16px;
    width: min(760px, calc(100vw - 32px));
    max-height: min(760px, calc(100vh - 32px));
    overflow: auto;
    border: 1px solid lightgray;
    border-radius: 8px;
    background: var(--panel);
    box-shadow: none;
    padding: 18px;
  }

  .model-modal-header {
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: start;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--line);
  }

  .model-modal-header p {
    margin-top: 6px;
    color: var(--muted-strong);
    font-size: 0.88rem;
    line-height: 1.35;
  }

  .modal-close {
    position: relative;
    display: grid;
    width: 32px;
    height: 32px;
    flex: 0 0 auto;
    place-items: center;
    border: 1px solid lightgray;
    border-radius: 999px;
    background: var(--panel-soft);
    color: var(--ink);
    cursor: pointer;
    padding: 0;
  }

  .modal-close::before,
  .modal-close::after {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 13px;
    height: 1.5px;
    border-radius: 999px;
    background: currentColor;
    content: "";
    transform-origin: center;
  }

  .modal-close::before {
    transform: translate(-50%, -50%) rotate(45deg);
  }

  .modal-close::after {
    transform: translate(-50%, -50%) rotate(-45deg);
  }

  .modal-close:hover,
  .modal-close:focus-visible {
    background: var(--panel);
    outline: 2px solid hsl(24 6% 17% / 0.2);
    outline-offset: 2px;
  }

  .detail-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .dataset-detail-metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .detail-metrics div,
  .detail-info-card {
    border: 1px solid lightgray;
    border-radius: 8px;
    background: var(--panel-soft);
    padding: 12px;
  }

  .detail-metrics span {
    display: block;
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .detail-metrics strong {
    display: block;
    margin-top: 8px;
    color: var(--ink);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 1.25rem;
    font-weight: 600;
  }

  .dataset-detail-metrics strong {
    font-size: 0.98rem;
    line-height: 1.2;
    overflow-wrap: anywhere;
  }

  .detail-info-card strong,
  .detail-section h3 {
    color: var(--ink);
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
  }

  .detail-info-card p {
    margin-top: 6px;
    color: var(--muted-strong);
    font-size: 0.86rem;
    line-height: 1.4;
  }

  .detail-section {
    display: grid;
    gap: 10px;
  }

  .detail-paper-link {
    width: fit-content;
    color: var(--ink);
    font-size: 0.9rem;
    font-weight: 600;
  }

  .author-list {
    display: grid;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .author-list li {
    display: grid;
    gap: 3px;
    border-bottom: 1px solid var(--line);
    padding-bottom: 8px;
  }

  .author-list li:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }

  .author-list strong {
    color: var(--ink);
    font-size: 0.9rem;
    font-weight: 600;
  }

  .author-list span {
    color: var(--muted-strong);
    font-size: 0.82rem;
    line-height: 1.35;
  }

  @media (max-width: 1180px) {
    .scatter-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 900px) {
    .filter-content {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 760px) {
    .panel-header {
      display: grid;
      align-items: start;
    }

    .filter-content {
      grid-template-columns: 1fr;
    }

    .dataset-filter {
      width: 100%;
    }

    .dataset-menu {
      position: static;
      width: 100%;
      max-height: 340px;
      margin-top: 6px;
    }

    .leaderboard-table {
      min-width: 820px;
    }

    .sticky-col {
      width: 160px !important;
      min-width: 160px !important;
    }

    .dataset-cell {
      padding: 0 8px !important;
    }

    .dataset-title-button {
      font-size: 0.86rem;
    }

    .matrix-table td strong {
      font-size: 0.86rem;
    }

    .scatter-grid {
      gap: 14px;
      padding: 12px 8px;
    }

    .scatter-plot h3 {
      font-size: 0.92rem;
    }

    .scatter-point-label {
      display: none;
    }

    .scatter-note {
      padding: 0 10px 14px;
      overflow-wrap: anywhere;
    }

    .modal-layer {
      padding: 12px;
    }

    .model-modal {
      width: calc(100vw - 24px);
      max-height: calc(100vh - 24px);
      padding: 14px;
    }

    .detail-metrics {
      grid-template-columns: 1fr;
    }
  }
</style>
