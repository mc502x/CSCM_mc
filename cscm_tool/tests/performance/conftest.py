"""Host-speed calibration for the timing-based performance tests.

The targets in docs/13-test-strategy.md §5 are stated for a reference
machine. A shared or throttled CI host can run the same code 2-3x slower
without any regression, which makes fixed limits flaky. Each test therefore
scales its *time limits* by `speed_factor`: how much slower this host runs a
fixed pure-Python workload than the reference. The factor is never below 1
(a fast host gets no extra headroom) and is capped at MAX_FACTOR, so a real
regression of more than that still fails. The factor used is recorded in the
test report next to every measurement.
"""

import hashlib
import time

import pytest

# Seconds the workload below took on the reference machine (an idle developer
# workstation, where the search p95 at 20,000 revisions measures ~50 ms).
REFERENCE_SECONDS = 0.075
MAX_FACTOR = 3.0


def _workload() -> float:
    start = time.perf_counter()
    digest = b"cscm"
    for _ in range(60_000):
        digest = hashlib.sha256(digest).digest()
    sorted(str(i * 7919 % 10007) for i in range(60_000))
    return time.perf_counter() - start


@pytest.fixture(scope="session")
def speed_factor() -> float:
    measured = min(_workload() for _ in range(5))
    return round(min(max(1.0, measured / REFERENCE_SECONDS), MAX_FACTOR), 2)
