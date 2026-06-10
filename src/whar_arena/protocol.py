import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from whar_arena.paths import PROTOCOL_PATH


@dataclass(frozen=True)
class Protocol:
    id: str
    data: dict[str, Any]
    digest: str

    @property
    def split_ids(self) -> list[str]:
        split_count = int(self.data["split"]["k"])
        return [f"split-{index:02d}" for index in range(split_count)]


def load_protocol(path: Path = PROTOCOL_PATH) -> Protocol:
    data = yaml.safe_load(path.read_text()) or {}
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return Protocol(id=str(data["id"]), data=data, digest=digest)
