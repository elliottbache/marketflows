import matplotlib

matplotlib.use("Agg")  # create plots in backend always

from marketflows.app import change_this_name_and_add_docstring
from marketflows.logging_utils import configure_logging


def main() -> int:

    #    configure_logging(level=cfg.log_level, node="CoinGecko", tutorial=cfg.tutorial)
    configure_logging()

    pass  # eraseme once this function has logic in it
    pass  # eraseme once this function has logic in it
    pass  # eraseme once this function has logic in it

    # parse args

    # call function to run pipeline
    # uncomment for integration tests (just running python, not pytest)
    change_this_name_and_add_docstring()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
