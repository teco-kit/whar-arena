from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = REPO_ROOT / "evaluation" / "protocol.yaml"
RESULTS_DIR = REPO_ROOT / "data" / "results"
SCHEMA_DIR = REPO_ROOT / "schemas"
WEB_GENERATED_DIR = REPO_ROOT / "apps" / "web" / "src" / "generated"
