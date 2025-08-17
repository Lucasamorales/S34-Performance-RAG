from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Dict, Optional, Tuple

# Cache: absolute path -> (mtime_ns, size, content)
_cache: Dict[str, Tuple[int, int, str]] = {}
_lock = RLock()


def _default_prompt_path() -> Path:
    return Path(__file__).resolve().parent / "rag_system.md"


def _resolve_path(path: Optional[str]) -> Path:
    """
    Resolve user-supplied or env path to an absolute Path.
    Expands ~ and env vars; errors if pointing to a directory.
    """
    p_str = path or os.getenv("PROMPT_FILE")
    p = Path(p_str).expanduser() if p_str else _default_prompt_path()
    # We let stat() raise for missing files, but reject directories early for clarity.
    if p.is_dir():
        raise IsADirectoryError(f"Expected a file, got directory: {p}")
    # Use strict=True to surface broken symlinks early.
    return p.resolve(strict=True)


def _normalize_newlines(text: str) -> str:
    # Keep content stable across platforms; avoids accidental cache misses upstream.
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def get_prompt(path: Optional[str] = None, *, force_reload: bool = False) -> str:
    """
    Load a prompt from a Markdown file with a small, mtime/size-based cache.

    - If `path` is None, try PROMPT_FILE env var; otherwise use default (rag_system.md).
    - Uses nanosecond mtime + size to avoid false negatives on coarse filesystems.
    - Thread-safe; avoids blocking the event loop in async apps.
    - `force_reload=True` bypasses the cache.
    """
    p = _resolve_path(path)
    key = str(p)

    # First stat (TOCTOU-safe reload below)
    stat1 = p.stat()
    mtime_ns, size = stat1.st_mtime_ns, stat1.st_size

    with _lock:
        entry = _cache.get(key)
        if not force_reload and entry and entry[0] == mtime_ns and entry[1] == size:
            return entry[2]

        # Read text and re-stat to detect modifications during read
        text = p.read_text(encoding="utf-8", errors="strict")
        stat2 = p.stat()
        if stat2.st_mtime_ns != mtime_ns or stat2.st_size != size:
            # File changed during read; read once more
            text = p.read_text(encoding="utf-8", errors="strict")
            stat2 = p.stat()

        text = _normalize_newlines(text)
        _cache[key] = (stat2.st_mtime_ns, stat2.st_size, text)
        return text


def clear_prompt_cache(path: Optional[str] = None) -> None:
    """
    Clear the whole cache or a single entry.
    """
    with _lock:
        if path is None:
            _cache.clear()
        else:
            try:
                p = _resolve_path(path)
            except Exception:
                # If resolution fails, nothing to remove
                return
            _cache.pop(str(p), None)
