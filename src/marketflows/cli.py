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

    parser = _parse_args(argv)
    ns = parser.parse_args(argv)

    configure_logging(level=ns.log_level, is_tutorial=ns.tutorial)

    secrets_path = Path.cwd() / ns.secrets
    config_path = Path.cwd() / ns.config
    out_dir = Path.cwd() / ns.out_dir
    run_pipeline(
        secrets_path=secrets_path,
        config_path=config_path,
        out_dir=out_dir,
        is_tutorial=ns.tutorial,
    )

    return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.ArgumentParser:
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


if __name__ == "__main__":
    raise SystemExit(main())
