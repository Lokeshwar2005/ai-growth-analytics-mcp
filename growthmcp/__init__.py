"""GrowthMCP package."""

from .core.server import main

__version__ = "0.1.0"


def entrypoint() -> None:
    main()
