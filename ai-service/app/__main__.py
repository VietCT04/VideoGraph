"""Run the dependency-free local HTTP fallback with ``python -m app``."""

from __future__ import annotations

from .api import StandardLibraryApplication, create_app


def main() -> None:
    application = create_app()
    if not isinstance(application, StandardLibraryApplication):
        raise SystemExit(
            "FastAPI is installed; run the returned app with an ASGI server such as uvicorn."
        )
    application.serve()


if __name__ == "__main__":
    main()
