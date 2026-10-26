"""Report the most severe drug-drug interaction for each line of input."""

__all__ = ["__version__"]


def __getattr__(name: str) -> str:
    """Resolve ``__version__`` lazily: importing package metadata costs more than a 10k-line run."""
    if name != "__version__":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("interactions")
    except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled checkout
        return "0.0.0+unknown"
