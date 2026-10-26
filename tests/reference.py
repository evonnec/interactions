"""Naive O(records) reference implementation, independent of the production index."""

from collections.abc import Iterable, Sequence
from typing import Any

SEVERITY_RANK = {"minor": 1, "moderate": 2, "major": 3}


def reference_result(records: Sequence[dict[str, Any]], line: str) -> str:
    """The spec rule, written the obvious way: scan every record in file order."""
    present = {token.casefold() for token in line.split()}
    best: tuple[int, dict[str, Any]] | None = None
    for record in records:
        first, second = (d.casefold() for d in record["drugs"])
        if first in present and second in present:
            rank = SEVERITY_RANK[record["severity"].casefold()]
            if best is None or rank > best[0]:  # strictly greater: the earliest record wins ties
                best = (rank, record)
    if best is None:
        return "No interaction"
    return f"{best[1]['severity'].upper()}: {best[1]['description']}"


def reference_output(records: Sequence[dict[str, Any]], lines: Iterable[str]) -> list[str]:
    return [reference_result(records, line) for line in lines]
