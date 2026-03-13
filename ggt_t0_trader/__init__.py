"""Hong Kong Stock Connect T0 momentum backtesting and visualization toolkit."""

from .backtest import BacktestEngine
from .data_loader import load_market_data
from .demo import build_demo_dataset
from .reporting import render_dashboard
from .strategy import HongKongT0MomentumStrategy

__all__ = [
    "BacktestEngine",
    "HongKongT0MomentumStrategy",
    "build_demo_dataset",
    "load_market_data",
    "render_dashboard",
]
