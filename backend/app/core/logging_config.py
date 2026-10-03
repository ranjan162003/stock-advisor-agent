from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    # yfinance is very chatty about individual failed tickers; we log those ourselves.
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
