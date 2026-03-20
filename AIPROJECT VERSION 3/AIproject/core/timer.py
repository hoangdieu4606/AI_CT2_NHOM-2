from __future__ import annotations

import time
from contextlib import contextmanager


@contextmanager
def measure_time():
    start = time.perf_counter()
    record = {"elapsed": None}
    try:
        yield record
    finally:
        record["elapsed"] = time.perf_counter() - start