import unittest

from ggt_t0_trader.backtest import BacktestEngine
from ggt_t0_trader.demo import build_demo_dataset


class BacktestTests(unittest.TestCase):
    def test_backtest_applies_take_profit_and_stop_rules(self) -> None:
        result = BacktestEngine().run(build_demo_dataset())
        self.assertGreaterEqual(len(result.trades), 3)
        self.assertLessEqual(len(result.trades), 5)
        reasons = [trade.exit_reason for trade in result.trades]
        self.assertIn("take_profit_5pct", reasons)
        self.assertIn("stop_loss", reasons)
        self.assertIn("time_stop", reasons)

    def test_backtest_metrics_are_calculated(self) -> None:
        result = BacktestEngine().run(build_demo_dataset())
        self.assertGreater(result.ending_capital, 0)
        self.assertEqual(result.metrics.trades, len(result.trades))
        self.assertGreater(result.metrics.win_rate_pct, 0)
        self.assertGreaterEqual(result.metrics.max_drawdown_pct, 0)
        self.assertIsNotNone(result.targets.win_rate_ok)


if __name__ == "__main__":
    unittest.main()
