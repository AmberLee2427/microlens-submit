"""
Legacy CLI entry point for microlens-submit.

This file is deprecated and will be removed in a future release.
Use `python -m microlens_submit.cli` or `microlens-submit` instead.
"""

from microlens_submit.cli.main import app

if __name__ == "__main__":
    import warnings
    warnings.warn(
        "microlens_submit/cli.py is deprecated. Use the new CLI package entry point instead.",
        DeprecationWarning,
    )
    app()
