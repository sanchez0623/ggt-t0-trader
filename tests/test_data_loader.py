import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ggt_t0_trader.backtest import BacktestEngine
from ggt_t0_trader.data_loader import load_market_data
from ggt_t0_trader.demo import build_demo_dataset


def _write_dataset_csv(data_dir: Path) -> None:
    dataset = build_demo_dataset()

    with (data_dir / "profiles.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "symbol",
                "name",
                "stock_connect_eligible",
                "float_market_cap_hkd",
                "avg_turnover_20d_hkd",
                "rsi_60m",
                "has_negative_announcement",
            ],
        )
        writer.writeheader()
        for security_day in dataset:
            writer.writerow(
                {
                    "symbol": security_day.profile.symbol,
                    "name": security_day.profile.name,
                    "stock_connect_eligible": str(security_day.profile.stock_connect_eligible).lower(),
                    "float_market_cap_hkd": security_day.profile.float_market_cap_hkd,
                    "avg_turnover_20d_hkd": security_day.profile.avg_turnover_20d_hkd,
                    "rsi_60m": security_day.profile.rsi_60m,
                    "has_negative_announcement": str(security_day.profile.has_negative_announcement).lower(),
                }
            )

    with (data_dir / "snapshots.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "symbol",
                "trading_day",
                "sample_time",
                "last_price",
                "auction_change_pct",
                "intraday_change_pct",
                "speed_3m_change_pct",
                "speed_3m_rank",
                "volume_ratio",
                "volume_ratio_rank",
                "block_buy_ratio",
                "ask_bid_notional_ratio",
                "southbound_net_buy_ratio",
                "spread_pct",
                "vwap",
                "post_open_peak_gain_pct",
            ],
        )
        writer.writeheader()
        for security_day in dataset:
            for sample_time, snapshot in sorted(security_day.snapshots.items()):
                writer.writerow(
                    {
                        "symbol": security_day.profile.symbol,
                        "trading_day": security_day.trading_day.isoformat(),
                        "sample_time": sample_time,
                        "last_price": snapshot.last_price,
                        "auction_change_pct": snapshot.auction_change_pct,
                        "intraday_change_pct": snapshot.intraday_change_pct,
                        "speed_3m_change_pct": snapshot.speed_3m_change_pct,
                        "speed_3m_rank": snapshot.speed_3m_rank,
                        "volume_ratio": snapshot.volume_ratio,
                        "volume_ratio_rank": snapshot.volume_ratio_rank,
                        "block_buy_ratio": snapshot.block_buy_ratio,
                        "ask_bid_notional_ratio": snapshot.ask_bid_notional_ratio,
                        "southbound_net_buy_ratio": snapshot.southbound_net_buy_ratio,
                        "spread_pct": snapshot.spread_pct,
                        "vwap": snapshot.vwap,
                        "post_open_peak_gain_pct": snapshot.post_open_peak_gain_pct,
                    }
                )

    with (data_dir / "bars.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "symbol",
                "timestamp",
                "price",
                "vwap",
                "spread_pct",
                "intraday_gain_pct",
                "post_open_peak_gain_pct",
                "ask_bid_notional_ratio",
                "hang_seng_change_pct",
                "hs300_change_pct",
                "triggered_vcm",
                "black_swan_event",
            ],
        )
        writer.writeheader()
        for security_day in dataset:
            for bar in security_day.bars:
                writer.writerow(
                    {
                        "symbol": security_day.profile.symbol,
                        "timestamp": bar.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "price": bar.price,
                        "vwap": bar.vwap,
                        "spread_pct": bar.spread_pct,
                        "intraday_gain_pct": bar.intraday_gain_pct,
                        "post_open_peak_gain_pct": bar.post_open_peak_gain_pct,
                        "ask_bid_notional_ratio": bar.ask_bid_notional_ratio,
                        "hang_seng_change_pct": bar.hang_seng_change_pct,
                        "hs300_change_pct": bar.hs300_change_pct,
                        "triggered_vcm": str(bar.triggered_vcm).lower(),
                        "black_swan_event": str(bar.black_swan_event).lower(),
                    }
                )


class DataLoaderTests(unittest.TestCase):
    def test_load_market_data_round_trips_demo_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            demo_dataset = build_demo_dataset()
            _write_dataset_csv(data_dir)

            loaded_dataset = load_market_data(data_dir)

            self.assertEqual(len(loaded_dataset), len(demo_dataset))
            self.assertEqual([item.profile.symbol for item in loaded_dataset], [item.profile.symbol for item in demo_dataset])
            self.assertEqual(loaded_dataset[0].snapshots["09:20"], demo_dataset[0].snapshots["09:20"])
            self.assertEqual(loaded_dataset[0].bars[0], demo_dataset[0].bars[0])

    def test_cli_accepts_external_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            output_path = data_dir / "dashboard.html"
            _write_dataset_csv(data_dir)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ggt_t0_trader",
                    "--data-dir",
                    str(data_dir),
                    "--output",
                    str(output_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("Dashboard written to", completed.stdout)
            self.assertTrue(output_path.exists())
            result = BacktestEngine().run(load_market_data(data_dir))
            self.assertGreaterEqual(len(result.trades), 3)


if __name__ == "__main__":
    unittest.main()
