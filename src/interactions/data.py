"""Loading and validating the interactions data file (this module performs the file I/O)."""

import json
import re
from importlib.resources import files
from pathlib import Path
from typing import Any

from interactions.model import Interaction, Severity, normalize

RECORD_KEYS = frozenset({"drugs", "severity", "description"})
# Characters that cannot appear in a description: C0/C1 controls except tab (this includes every
# line break: \n \r \v \f \x1c-\x1e \x85), U+2028/U+2029 and lone surrogates (not encodable as
# UTF-8). A description is printed verbatim, so a line break would break "one line out per line in".
UNPRINTABLE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f-\x9f\u2028\u2029\ud800-\udfff]")


class DataError(Exception):
    """The interactions data is missing, unreadable or invalid."""


def _parse_record(raw: object) -> Interaction:
    """Validate one record; raise ``DataError`` (without a record index) on a defect."""
    if not isinstance(raw, dict):
        raise DataError(f"record must be an object, got {type(raw).__name__}")
    record: dict[str, Any] = raw
    missing = sorted(RECORD_KEYS - record.keys())
    if missing:
        raise DataError(f"missing key(s): {', '.join(missing)}")
    unknown = sorted(str(k) for k in record.keys() - RECORD_KEYS)
    if unknown:
        raise DataError(f"unknown key(s): {', '.join(unknown)}")

    drugs = record["drugs"]
    if not isinstance(drugs, list):
        raise DataError("drugs must be an array of strings")
    if len(drugs) != 2:
        raise DataError(f"drugs must have exactly 2 distinct names, got {len(drugs)}")
    if not all(isinstance(d, str) for d in drugs):
        raise DataError("drugs must be an array of strings")
    first, second = (normalize(d) for d in drugs)
    if not first or not second:
        raise DataError("drug names must not be empty")
    if first.split() != [first] or second.split() != [second]:
        raise DataError("drug names must not contain whitespace")
    if first == second:
        raise DataError(f"drugs must be 2 distinct names, got {first!r} twice")

    severity = record["severity"]
    if not isinstance(severity, str):
        raise DataError("severity must be a string")
    try:
        parsed_severity = Severity.parse(severity)
    except ValueError as error:
        raise DataError(str(error)) from None

    description = record["description"]
    if not isinstance(description, str) or not description.strip():
        raise DataError("description must be a non-empty string")
    if UNPRINTABLE.search(description):
        raise DataError("description must be a single line without control characters")

    return Interaction(drugs=(first, second), severity=parsed_severity, description=description)


def parse_records(raw: object) -> list[Interaction]:
    """Validate parsed JSON and convert it to interactions, preserving file order."""
    if not isinstance(raw, list):
        raise DataError(f"top level must be an array of records, got {type(raw).__name__}")
    interactions: list[Interaction] = []
    for index, item in enumerate(raw):
        try:
            interactions.append(_parse_record(item))
        except DataError as error:
            raise DataError(f"record {index}: {error}") from None
    return interactions


def load_file(path: Path) -> list[Interaction]:
    """Read, parse and validate a data file; every failure is reported as ``DataError``."""
    try:
        text = path.read_text(encoding="utf-8-sig")  # tolerate a BOM written by Windows editors
    except FileNotFoundError:
        raise DataError(f"data file not found: {path}") from None
    except UnicodeDecodeError:
        raise DataError(f"{path}: not valid UTF-8") from None
    except OSError as error:
        raise DataError(f"cannot read data file {path}: {error.strerror or error}") from None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise DataError(
            f"{path}: invalid JSON at line {error.lineno} col {error.colno}: {error.msg}"
        ) from None
    except RecursionError:
        raise DataError(f"{path}: invalid JSON: nested too deeply") from None
    except ValueError as error:  # e.g. an integer with more than 4300 digits
        raise DataError(f"{path}: invalid JSON: {error}") from None
    try:
        return parse_records(raw)
    except DataError as error:
        raise DataError(f"{path}: {error}") from None


def bundled_data_path() -> Path:
    """Path of the ``interactions.json`` shipped inside the package."""
    return Path(str(files("interactions") / "data" / "interactions.json"))


def load_bundled() -> list[Interaction]:
    """Load the dataset bundled with the package."""
    return load_file(bundled_data_path())
