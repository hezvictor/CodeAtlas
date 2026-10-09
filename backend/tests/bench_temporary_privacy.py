"""Manual benchmark for the temporary-answer privacy gate.

Run from ``backend`` with the project's Python environment:
    python tests/bench_temporary_privacy.py
"""

import sys
import tracemalloc
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.temporary.privacy import validate_answer  # noqa: E402


def _measure(name: str, source: str, answer: str) -> None:
    tracemalloc.start()
    started = perf_counter()
    try:
        validate_answer(answer, [{"text": source, "filename": "benchmark.txt"}], [])
        outcome = "accepted"
    except ValueError as error:
        outcome = str(error)
    elapsed = perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"{name}: {elapsed:.4f}s, peak={peak / 1024 / 1024:.2f}MiB ({outcome})")


if __name__ == "__main__":
    _measure("100k repeated source / 1k late contiguous quote", "a" * 100_000,
             "b" * 32 + "a" * 1_000 + "c" * 32)
    _measure("2m source / 1k unrelated answer", "a" * 2_000_000,
             "b" * 1_000)
