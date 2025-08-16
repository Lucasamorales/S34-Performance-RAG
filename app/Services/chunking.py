# Chunking utilities for splitting text into overlapping windows.
from __future__ import annotations

from typing import Generator, List, Tuple

def iter_chunks(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> Generator[Tuple[int, str], None, None]:    
    """
    Yield (index, chunk) pairs from the input text, using a sliding window.

    Args:
        text (str): The input text to split.
        chunk_size (int): The size of each chunk (must be > 0).
        overlap (int): The number of characters to overlap between chunks (0 <= overlap < chunk_size).

    Yields:
        Tuple[int, str]: (chunk_index, chunk_text) for each chunk.

    Raises:
        ValueError: If chunk_size or overlap are invalid.
    """
    if not text:
        # No text to chunk; yield nothing.
        return
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        # Enforce valid chunking parameters.
        raise ValueError("Invalid chunking parameters: require chunk_size > 0 and 0 <= overlap < chunk_size.")

    n = len(text)
    step = chunk_size - overlap  # Always > 0 due to validation.
    idx = 0
    start = 0

    # Fast path: if text fits in one chunk, yield it and return.
    if n <= chunk_size:
        yield 0, text
        return

    # Main sliding window loop.
    while start < n:
        end = start + chunk_size
        # Slicing past end of string is safe in Python.
        chunk = text[start:end]
        if not chunk:
            # Defensive: should not occur, but protects against edge errors.
            break
        yield idx, chunk
        idx += 1
        start += step  # Advance window by step size.

def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> List[Tuple[int, str]]:
    """
    Materialize all (index, chunk) pairs from the input text as a list.

    Args:
        text (str): The input text to split.
        chunk_size (int): The size of each chunk (must be > 0).
        overlap (int): The number of characters to overlap between chunks (0 <= overlap < chunk_size).

    Returns:
        List[Tuple[int, str]]: List of (chunk_index, chunk_text) pairs.

    Note:
        Prefer `iter_chunks()` for streaming large inputs to reduce memory usage.
    """
    return list(iter_chunks(text, chunk_size=chunk_size, overlap=overlap))
