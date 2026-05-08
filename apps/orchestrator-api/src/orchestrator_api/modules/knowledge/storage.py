from __future__ import annotations

import hashlib
from pathlib import Path

from orchestrator_api.core.settings import get_settings


def _storage_root() -> Path:
    settings = get_settings()
    return Path(settings.storage_path)


def save_original_bytes(*, document_id: str, version_id: str, filename: str, data: bytes) -> tuple[str, str]:
    """
    Returns (relative_path, sha256_hex)
    """
    sha = hashlib.sha256(data).hexdigest()
    safe_name = filename.replace("\\", "_").replace("/", "_")
    rel = Path("originals") / document_id / f"{version_id}_{safe_name}"
    full = _storage_root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    return str(rel).replace("\\", "/"), sha

