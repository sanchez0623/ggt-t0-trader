import unittest

from ggt_t0_trader.demo import build_demo_dataset
from ggt_t0_trader.models import MIDDAY_SAMPLING_TIMES, MORNING_SAMPLING_TIMES
from ggt_t0_trader.strategy import HongKongT0MomentumStrategy


class StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.strategy = HongKongT0MomentumStrategy()
        self.dataset = build_demo_dataset()

    def test_sampling_windows_match_requirement(self) -> None:
        self.assertEqual(MORNING_SAMPLING_TIMES, ("09:20", "09:25", "09:28", "09:32", "09:34", "09:36", "09:38", "09:40"))
        self.assertEqual(MIDDAY_SAMPLING_TIMES, ("13:00", "13:05"))

    def test_scoring_filters_out_non_eligible_names(self) -> None:
        morning_scores = self.strategy.score_morning_candidates(self.dataset)
        symbols = [candidate.symbol for candidate in morning_scores]
        self.assertEqual(symbols[:3], ["02201.HK", "03988.HK", "06618.HK"])
        self.assertNotIn("09977.HK", symbols)
        self.assertGreater(morning_scores[0].total_score, morning_scores[1].total_score)

    def test_portfolio_respects_weight_caps(self) -> None:
        selection = self.strategy.build_portfolio(self.strategy.score_morning_candidates(self.dataset))
        self.assertLessEqual(selection.per_position_weight, 0.2)
        self.assertLessEqual(selection.total_weight, 0.8)
        self.assertGreaterEqual(len(selection.positions), 3)
        self.assertLessEqual(len(selection.positions), 5)

    def test_midday_scan_produces_secondary_candidates(self) -> None:
        midday_scores = self.strategy.score_midday_candidates(self.dataset)
        self.assertTrue(midday_scores)
        self.assertEqual(midday_scores[0].symbol, "02201.HK")


if __name__ == "__main__":
    unittest.main()
