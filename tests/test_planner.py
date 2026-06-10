from whar_arena.catalog import discover_datasets, discover_models
from whar_arena.planner import plan_runs
from whar_arena.protocol import load_protocol


def test_catalog_discovers_benchmark_inputs() -> None:
    assert any(dataset.id == "wisdm" for dataset in discover_datasets())
    model_ids = {model.id for model in discover_models()}
    assert "tinyhar" in model_ids
    assert len(model_ids) >= 17


def test_planner_expands_protocol_matrix() -> None:
    protocol = load_protocol()
    runs = plan_runs(protocol=protocol, only_model="tinyhar", only_dataset="wisdm")

    assert len(runs) == 10
    assert {run.split_id for run in runs} == {f"split-{i:02d}" for i in range(10)}
    assert all(run.protocol_id == "whar_arena_v1" for run in runs)


def test_planner_caps_subject_group_splits_by_dataset_subject_count() -> None:
    protocol = load_protocol()
    runs = plan_runs(
        protocol=protocol,
        only_model="tinyhar",
        only_dataset="actrectut_gestures",
    )

    assert len(runs) == 2
    assert {run.split_id for run in runs} == {"split-00", "split-01"}


def test_protocol_matches_har_benchmarking_strategy() -> None:
    protocol = load_protocol()

    assert protocol.data["window"] == {
        "duration_seconds": 3,
        "overlap": 0.5,
        "sampling_rate": "native",
    }
    assert protocol.data["preprocessing"] == {
        "normalization": "global_standardization",
        "fit_normalization_on": "train",
    }
    assert protocol.data["split"] == {
        "strategy": "k_subject_groups",
        "k": 10,
        "validation_fraction": 0.2,
        "validation_source": "train_subjects",
    }

    deep_training = protocol.data["training"]["deep"]
    assert deep_training["optimizer"] == "adamw"
    assert deep_training["learning_rate"] == 0.001
    assert deep_training["scheduler"] == "cosine_annealing"
    assert deep_training["weight_decay"] == 0.0001
    assert deep_training["batch_size"] == 64
    assert deep_training["max_epochs"] == 100
    assert deep_training["early_stopping"] == {
        "monitor": "val_macro_f1",
        "patience": 10,
        "restore_best": True,
    }
    assert deep_training["loss"] == {
        "type": "weighted_cross_entropy",
        "class_weights": "train_frequency",
    }
