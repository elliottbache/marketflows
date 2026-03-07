"""Command-line interface for MarketFlows.

Parses CLI flags, configures logging, resolves paths, and runs the pipeline.
"""
import argparse
from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # create plots in backend always

from marketflows.app import run_pipeline
from marketflows.logging_utils import configure_logging

_DEFAULT_CONFIG_FILE = "config.toml"
_DEFAULT_SECRETS_FILE = "secrets.toml"
_DEFAULT_OUTPUT_DIR = "output_plots"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the MarketFlows CLI entrypoint.

    Parses command-line arguments, configures logging, resolves file paths, and
    invokes the main pipeline runner.

    Args:
        argv: Optional argument vector (excluding the program name). If None,
            arguments are read from the process command line.

    Returns:
        Exit code (0 on success).

    Raises:
        SystemExit: When invoked via the module entrypoint (see __main__ guard),
            argparse may call SystemExit on invalid CLI arguments.
    """
    parser = _parse_args()
    ns = parser.parse_args(argv)

    configure_logging(level=ns.log_level, is_tutorial=ns.tutorial)

    secrets_path = _resolve_path(ns.secrets)
    config_path = _resolve_path(ns.config)
    out_dir = _resolve_path(ns.out_dir)
    run_pipeline(
        secrets_path=secrets_path,
        config_path=config_path,
        out_dir=out_dir,
        is_tutorial=ns.tutorial,
    )

    return 0


def _parse_args() -> argparse.ArgumentParser:
    """Parse args from command line."""
    parser = argparse.ArgumentParser(
        prog="marketflows",
        description="Track capital flows and narrative rotation across markets.",
    )

    parser.add_argument(
        "--config",
        default=_DEFAULT_CONFIG_FILE,
        help=f"configuration parameters in .toml format (default: {_DEFAULT_CONFIG_FILE})",
    )

    parser.add_argument(
        "--secrets",
        default=_DEFAULT_SECRETS_FILE,
        help=f"secrets configuration parameters in .toml format (default: {_DEFAULT_SECRETS_FILE})",
    )

    parser.add_argument(
        "--out-dir",
        default=_DEFAULT_OUTPUT_DIR,
        help=f"output directory for plots and tables (default: {_DEFAULT_OUTPUT_DIR})",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )

    parser.add_argument(
        "--tutorial",
        action="store_true",
        help="read predefined configuration and provider data (useful for testing correct installation)",
    )

    return parser


def _resolve_path(p: str) -> Path:
    path = Path(p).expanduser()
    out_path = path if path.is_absolute() else (Path.cwd() / path)

    return out_path


if __name__ == "__main__":
    raise SystemExit(main())
