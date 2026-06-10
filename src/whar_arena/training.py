from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import balanced_accuracy_score
from torch import nn
from torch.utils.data import DataLoader

from whar_datasets import (
    LKSOSplitter,
    Loader,
    PostProcessingPipeline,
    PreProcessingPipeline,
    TorchAdapter,
    WHARDatasetID,
    get_dataset_cfg,
)
from whar_datasets.splitting.split import Split
from whar_datasets.utils.types import NormType
from whar_models import WHARModelID, build_model

from whar_arena.catalog import DatasetEntry, ModelEntry, discover_datasets, discover_models
from whar_arena.planner import fingerprint_run, result_path_for
from whar_arena.protocol import Protocol, load_protocol


@dataclass(frozen=True)
class SplitMetrics:
    split_id: str
    macro_f1: float
    accuracy: float
    balanced_accuracy: float
    best_epoch: int | None
    epochs_ran: int
    split_identifier: str
    train_size: int
    val_size: int
    test_size: int


def run_benchmark(
    *,
    model_id: str | WHARModelID,
    dataset_id: str | WHARDatasetID,
    datasets_dir: Path,
    output_dir: Path,
    protocol: Protocol | None = None,
    max_epochs: int | None = None,
    patience: int | None = None,
    limit_splits: int | None = None,
    skip_existing: bool = True,
) -> list[SplitMetrics]:
    """Run the protocol-backed benchmark for one model/dataset pair.

    This mirrors the HAR-Benchmarking experiment strategy:
    K-subject-group splits, train-only post-processing statistics, TorchAdapter
    dataloaders, weighted cross-entropy from train windows, cosine LR scheduling,
    validation macro-F1 early stopping, and best-state restoration.
    """

    protocol = protocol or load_protocol()
    model_enum = _coerce_model_id(model_id)
    dataset_enum = _coerce_dataset_id(dataset_id)
    model_entry = _catalog_model(model_enum.value)
    dataset_entry = _catalog_dataset(dataset_enum.value)

    cfg = _configure_dataset_cfg(
        protocol=protocol,
        dataset_id=dataset_enum,
        datasets_dir=datasets_dir,
        max_epochs=max_epochs,
    )
    training_cfg = _deep_training_cfg(protocol)
    epochs = int(max_epochs or cfg.num_epochs)
    early_stopping_patience = int(
        patience
        if patience is not None
        else training_cfg["early_stopping"]["patience"]
    )

    _seed_everything(cfg.seed)
    pre_pipeline = PreProcessingPipeline(cfg)
    _, session_df, window_df = pre_pipeline.run()
    splits = LKSOSplitter(cfg).get_splits(session_df, window_df)
    if limit_splits is not None:
        splits = splits[:limit_splits]

    metrics: list[SplitMetrics] = []
    for split_index, split in enumerate(splits):
        split_id = f"split-{split_index:02d}"
        fingerprint = fingerprint_run(protocol, model_entry, dataset_entry, split_id)
        result_path = result_path_for(
            protocol.id,
            model_entry.id,
            dataset_entry.id,
            split_id,
        )
        if skip_existing and _result_matches(result_path, fingerprint):
            print(
                f"{model_entry.id}/{dataset_entry.id}/{split_id}: existing result matches protocol; skipping.",
                flush=True,
            )
            continue

        post_pipeline = PostProcessingPipeline(
            cfg,
            pre_pipeline,
            window_df,
            split.train_indices,
        )
        samples = post_pipeline.run()
        loader = Loader(session_df, window_df, post_pipeline.samples_dir, samples)
        split_metrics = _run_split(
            cfg=cfg,
            protocol=protocol,
            model_enum=model_enum,
            model_entry=model_entry,
            loader=loader,
            split=split,
            split_id=split_id,
            max_epochs=epochs,
            patience=early_stopping_patience,
        )
        metrics.append(split_metrics)
        _write_result(
            protocol=protocol,
            model=model_entry,
            dataset=dataset_entry,
            metrics=split_metrics,
            output_dir=output_dir,
        )

    _write_summary(
        protocol=protocol,
        model=model_entry,
        dataset=dataset_entry,
        metrics=metrics,
        output_dir=output_dir,
    )
    return metrics


def _run_split(
    *,
    cfg: Any,
    protocol: Protocol,
    model_enum: WHARModelID,
    model_entry: ModelEntry,
    loader: Loader,
    split: Split,
    split_id: str,
    max_epochs: int,
    patience: int,
) -> SplitMetrics:
    adapter = TorchAdapter(cfg, loader, split)
    dataloaders = adapter.get_dataloaders(batch_size=cfg.batch_size)
    window_length, input_channels, num_classes = _infer_dataset_shape(dataloaders, cfg)
    model = build_model(
        model_enum,
        input_channels=input_channels,
        window_length=window_length,
        num_classes=num_classes,
        **_model_kwargs(protocol, model_entry),
    )

    if model_entry.framework == "sklearn":
        return _fit_classical_split(
            cfg=cfg,
            model=model,
            dataloaders=dataloaders,
            split=split,
            split_id=split_id,
        )
    if not isinstance(model, nn.Module):
        raise TypeError(f"{model_entry.id} did not build a torch.nn.Module.")
    return _fit_torch_split(
        cfg=cfg,
        model=model,
        dataloaders=dataloaders,
        loader=loader,
        split=split,
        split_id=split_id,
        max_epochs=max_epochs,
        patience=patience,
        weight_decay=float(_deep_training_cfg(protocol)["weight_decay"]),
    )


def _fit_torch_split(
    *,
    cfg: Any,
    model: nn.Module,
    dataloaders: dict[str, DataLoader],
    loader: Loader,
    split: Split,
    split_id: str,
    max_epochs: int,
    patience: int,
    weight_decay: float,
) -> SplitMetrics:
    device = _get_device()
    model = model.to(device)
    class_weights = _class_weights(loader, split.train_indices, cfg.num_of_activities).to(
        device
    )
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(cfg.learning_rate),
        weight_decay=weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(max_epochs, 1),
    )

    best_state: dict[str, torch.Tensor] | None = None
    best_macro_f1 = float("-inf")
    best_epoch: int | None = None
    stale_epochs = 0
    epochs_ran = 0
    for epoch_index in range(max_epochs):
        epoch_number = epoch_index + 1
        epochs_ran = epoch_number
        model.train()
        for labels, inputs in dataloaders["train"]:
            labels = _target_labels(labels).to(device)
            inputs = _to_model_inputs(inputs, cfg).to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        val_metrics = _evaluate(
            model,
            dataloaders["val"],
            device=device,
            cfg=cfg,
            criterion=criterion,
        )
        val_macro_f1 = val_metrics["macro_f1"]
        print(
            f"{split_id} epoch {epoch_number:03d}: val_macro_f1={val_macro_f1:.4f}",
            flush=True,
        )

        if val_macro_f1 > best_macro_f1:
            best_macro_f1 = val_macro_f1
            best_epoch = epoch_number
            stale_epochs = 0
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
        else:
            stale_epochs += 1
            if stale_epochs >= patience:
                break

        scheduler.step()

    if best_state is not None:
        model.load_state_dict(best_state)
    test_metrics = _evaluate(
        model,
        dataloaders["test"],
        device=device,
        cfg=cfg,
        criterion=criterion,
    )
    return SplitMetrics(
        split_id=split_id,
        macro_f1=test_metrics["macro_f1"],
        accuracy=test_metrics["accuracy"],
        balanced_accuracy=test_metrics["balanced_accuracy"],
        best_epoch=best_epoch,
        epochs_ran=epochs_ran,
        split_identifier=split.identifier,
        train_size=len(split.train_indices),
        val_size=len(split.val_indices),
        test_size=len(split.test_indices),
    )


def _fit_classical_split(
    *,
    cfg: Any,
    model: Any,
    dataloaders: dict[str, DataLoader],
    split: Split,
    split_id: str,
) -> SplitMetrics:
    x_train, y_train = _collect_loader_tensors(dataloaders["train"], cfg)
    model.fit(x_train, y_train)
    test_metrics = _evaluate(
        model,
        dataloaders["test"],
        device=torch.device("cpu"),
        cfg=cfg,
        criterion=None,
    )
    return SplitMetrics(
        split_id=split_id,
        macro_f1=test_metrics["macro_f1"],
        accuracy=test_metrics["accuracy"],
        balanced_accuracy=test_metrics["balanced_accuracy"],
        best_epoch=None,
        epochs_ran=0,
        split_identifier=split.identifier,
        train_size=len(split.train_indices),
        val_size=len(split.val_indices),
        test_size=len(split.test_indices),
    )


def _evaluate(
    model: nn.Module,
    loader: DataLoader,
    *,
    device: torch.device,
    cfg: Any,
    criterion: nn.Module | None,
) -> dict[str, float]:
    was_training = model.training
    model.eval()
    total_loss = 0.0
    loss_weight = 0
    y_true: list[int] = []
    y_pred: list[int] = []

    with torch.no_grad():
        for labels, inputs in loader:
            targets = _target_labels(labels).to(device)
            inputs = _to_model_inputs(inputs, cfg).to(device)
            logits = model(inputs)
            if criterion is not None:
                loss = criterion(logits, targets)
                total_loss += float(loss.item()) * int(logits.size(0))
                loss_weight += int(logits.size(0))
            predictions = logits.argmax(dim=1)
            y_true.extend(targets.detach().cpu().numpy().astype(int).tolist())
            y_pred.extend(predictions.detach().cpu().numpy().astype(int).tolist())

    if was_training:
        model.train()

    metrics = _classification_metrics(y_true, y_pred, int(cfg.num_of_activities))
    metrics["loss"] = total_loss / loss_weight if loss_weight else 0.0
    return metrics


def _classification_metrics(
    y_true: list[int],
    y_pred: list[int],
    num_classes: int,
) -> dict[str, float]:
    if not y_true:
        return {"macro_f1": 0.0, "accuracy": 0.0, "balanced_accuracy": 0.0}

    targets = torch.tensor(y_true, dtype=torch.long)
    predictions = torch.tensor(y_pred, dtype=torch.long)
    accuracy = float((predictions == targets).to(torch.float32).mean().item())
    return {
        "macro_f1": _macro_f1(predictions, targets, num_classes),
        "accuracy": accuracy,
        "balanced_accuracy": float(
            balanced_accuracy_score(y_true, y_pred)
        ),
    }


def _macro_f1(preds: torch.Tensor, targets: torch.Tensor, num_classes: int) -> float:
    confusion = torch.bincount(
        targets * num_classes + preds,
        minlength=num_classes * num_classes,
    ).reshape(num_classes, num_classes)

    tp = confusion.diag().to(torch.float32)
    fp = confusion.sum(dim=0).to(torch.float32) - tp
    fn = confusion.sum(dim=1).to(torch.float32) - tp
    denom = 2 * tp + fp + fn
    f1_per_class = torch.where(denom > 0, (2 * tp) / denom, torch.zeros_like(denom))
    return float(f1_per_class.mean().item())


def _infer_dataset_shape(
    dataloaders: dict[str, DataLoader],
    cfg: Any,
) -> tuple[int, int, int]:
    labels, inputs = next(iter(dataloaders["train"]))
    _ = labels
    if inputs.ndim != 3:
        raise ValueError(
            f"Expected training inputs shaped as (B, L, C); got {tuple(inputs.shape)}"
        )

    window_length = int(inputs.shape[1])
    input_channels = int(inputs.shape[2])
    num_classes = int(cfg.num_of_activities)
    return window_length, input_channels, num_classes


def _collect_loader_tensors(
    loader: DataLoader,
    cfg: Any,
) -> tuple[torch.Tensor, torch.Tensor]:
    x_batches: list[torch.Tensor] = []
    y_batches: list[torch.Tensor] = []
    for labels, inputs in loader:
        x_batches.append(_to_model_inputs(inputs, cfg))
        y_batches.append(_target_labels(labels))
    return torch.cat(x_batches, dim=0), torch.cat(y_batches, dim=0)


def _to_model_inputs(inputs: torch.Tensor, cfg: Any) -> torch.Tensor:
    if inputs.ndim == 3 and inputs.shape[-1] == int(cfg.num_of_channels):
        return inputs.transpose(1, 2).contiguous()
    return inputs


def _target_labels(labels: torch.Tensor) -> torch.Tensor:
    if labels.ndim > 1:
        return labels.argmax(dim=1).to(torch.long)
    return labels.to(torch.long)


def _class_weights(loader: Loader, indices: list[int], num_classes: int) -> torch.Tensor:
    class_weights = loader.get_class_weights(indices)
    return torch.tensor(
        [
            max(float(class_weights.get(class_id, -1.0)), 0.0)
            for class_id in range(num_classes)
        ],
        dtype=torch.float32,
    )


def _configure_dataset_cfg(
    *,
    protocol: Protocol,
    dataset_id: WHARDatasetID,
    datasets_dir: Path,
    max_epochs: int | None,
) -> Any:
    cfg = get_dataset_cfg(dataset_id, datasets_dir=str(datasets_dir))
    window_cfg = protocol.data["window"]
    split_cfg = protocol.data["split"]
    training_cfg = _deep_training_cfg(protocol)

    cfg.window_time = float(window_cfg["duration_seconds"])
    cfg.window_overlap = float(window_cfg["overlap"])
    cfg.num_folds = int(split_cfg["k"])
    cfg.num_subject_groups = int(split_cfg["k"])
    cfg.val_percentage = float(split_cfg["validation_fraction"])
    cfg.normalization = _normalization_from_protocol(protocol)
    cfg.batch_size = int(training_cfg["batch_size"])
    cfg.learning_rate = float(training_cfg["learning_rate"])
    cfg.num_epochs = int(max_epochs or training_cfg["max_epochs"])
    cfg.seed = int(protocol.data.get("seed", getattr(cfg, "seed", 0)))
    cfg.in_memory = True
    cfg.parallelize = True
    cfg.cache_each_split = True
    return cfg


def _normalization_from_protocol(protocol: Protocol) -> NormType:
    normalization = protocol.data["preprocessing"]["normalization"]
    if normalization == "global_standardization":
        return NormType.STD_GLOBALLY
    raise ValueError(f"Unsupported normalization strategy: {normalization}")


def _deep_training_cfg(protocol: Protocol) -> dict[str, Any]:
    return protocol.data["training"]["deep"]


def _model_kwargs(protocol: Protocol, model: ModelEntry) -> dict[str, Any]:
    if model.framework != "sklearn":
        return {}
    classical_cfg = protocol.data["training"]["classical"]["models"]
    return dict(classical_cfg.get(model.id, {}))


def _write_result(
    *,
    protocol: Protocol,
    model: ModelEntry,
    dataset: DatasetEntry,
    metrics: SplitMetrics,
    output_dir: Path,
) -> None:
    fingerprint = fingerprint_run(protocol, model, dataset, metrics.split_id)
    result = {
        "protocol_id": protocol.id,
        "protocol_hash": protocol.digest,
        "model_id": model.id,
        "dataset_id": dataset.id,
        "split_id": metrics.split_id,
        "fingerprint": fingerprint,
        "status": "complete",
        "metrics": {
            "macro_f1": metrics.macro_f1,
            "accuracy": metrics.accuracy,
            "balanced_accuracy": metrics.balanced_accuracy,
        },
        "source": {
            "kind": "local_training",
            "framework": model.framework,
            "split_identifier": metrics.split_identifier,
            "train_size": metrics.train_size,
            "val_size": metrics.val_size,
            "test_size": metrics.test_size,
            "best_epoch": metrics.best_epoch,
            "epochs_ran": metrics.epochs_ran,
        },
    }

    path = result_path_for(protocol.id, model.id, dataset.id, metrics.split_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{metrics.split_id}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )


def _write_summary(
    *,
    protocol: Protocol,
    model: ModelEntry,
    dataset: DatasetEntry,
    metrics: list[SplitMetrics],
    output_dir: Path,
) -> None:
    macro_f1_values = [item.macro_f1 for item in metrics]
    summary = {
        "model_id": model.id,
        "dataset_id": dataset.id,
        "protocol_id": protocol.id,
        "protocol_hash": protocol.digest,
        "splits": [asdict(item) for item in metrics],
        "mean_macro_f1": float(np.mean(macro_f1_values)) if macro_f1_values else None,
        "std_macro_f1": float(np.std(macro_f1_values, ddof=1))
        if len(macro_f1_values) > 1
        else 0.0,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{model.id}_{dataset.id}_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )


def _result_matches(path: Path, fingerprint: str) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False
    return data.get("fingerprint") == fingerprint and data.get("status") == "complete"


def _coerce_model_id(model_id: str | WHARModelID) -> WHARModelID:
    if isinstance(model_id, WHARModelID):
        return model_id
    return WHARModelID(str(model_id))


def _coerce_dataset_id(dataset_id: str | WHARDatasetID) -> WHARDatasetID:
    if isinstance(dataset_id, WHARDatasetID):
        return dataset_id
    return WHARDatasetID(str(dataset_id))


def _catalog_model(model_id: str) -> ModelEntry:
    for model in discover_models():
        if model.id == model_id:
            return model
    raise ValueError(f"Unknown model in catalog: {model_id}")


def _catalog_dataset(dataset_id: str) -> DatasetEntry:
    for dataset in discover_datasets():
        if dataset.id == dataset_id:
            return dataset
    raise ValueError(f"Unknown dataset in catalog: {dataset_id}")


def _seed_everything(seed: int) -> None:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def _get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")
