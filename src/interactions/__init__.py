"""Report the most severe drug-drug interaction for each line of input."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("interactions")
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled checkout
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
