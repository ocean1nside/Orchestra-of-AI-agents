from __future__ import annotations

from pathlib import Path

from orchestrator_api.core.settings import get_settings


def read_original_text(*, relative_path: str) -> tuple[str, str]:
    """
    Read UTF-8 text from storage. Returns (text, inferred_suffix).
    Supported: .md, .txt (by path suffix).
    """
    root = Path(get_settings().storage_path)
    full = (root / relative_path).resolve()
    if not str(full).startswith(str(root.resolve())):
        raise ValueError("Invalid original path")
    if not full.is_file():
        raise FileNotFoundError(f"Original not found: {relative_path}")

    suffix = full.suffix.lower()
    raw = full.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("Only UTF-8 text files are supported for MVP") from e

    if suffix not in {".md", ".txt", ""}:
        raise ValueError(f"Unsupported file type for MVP: {suffix or 'no suffix'}")

    return text, suffix or ".txt"
