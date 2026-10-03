import math

import pandas as pd
import pytest

from app.analysis.technical_indicators import (
    annualized_volatility_percent,
    compute_technical_indicators,
    max_drawdown_percent,
    relative_strength_index,
    simple_moving_average,
    trailing_return_percent,
)


def test_simple_moving_average_uses_last_window_only():
    closes = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert simple_moving_average(closes, 2) == 4.5
    assert simple_moving_average(closes, 10) is None


def test_rsi_is_100_for_a_series_that_only_rises():
    closes = pd.Series(range(1, 40), dtype=float)
    assert relative_strength_index(closes) == 100.0


def test_rsi_is_low_for_a_series_that_only_falls():
    closes = pd.Series(range(40, 1, -1), dtype=float)
    assert relative_strength_index(closes) == pytest.approx(0.0, abs=1e-9)


def test_trailing_return_percent():
    closes = pd.Series([100, 105, 110, 120], dtype=float)
    assert trailing_return_percent(closes, 3) == pytest.approx(20.0)
    assert trailing_return_percent(closes, 4) is None


def test_volatility_is_zero_for_constant_growth_rate():
    closes = pd.Series([100 * 1.01**i for i in range(60)])
    assert annualized_volatility_percent(closes) == pytest.approx(0.0, abs=1e-9)


def test_max_drawdown_finds_worst_peak_to_trough():
    closes = pd.Series([100, 120, 90, 110, 60, 80], dtype=float)
    assert max_drawdown_percent(closes) == pytest.approx(-50.0)


def test_compute_technical_indicators_on_a_full_year():
    closes = pd.Series([100 + math.sin(i / 5) * 5 + i * 0.1 for i in range(252)])
    indicators = compute_technical_indicators(closes)
    assert indicators.last_close == round(closes.iloc[-1], 2)
    assert indicators.sma_200 is not None
    assert indicators.return_1y_percent is not None
    assert 0 <= indicators.rsi_14 <= 100
