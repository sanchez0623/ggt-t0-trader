from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from .models import InstrumentProfile, PriceBar, SampleSnapshot, SecurityDay


def load_market_data(data_dir: str | Path) -> list[SecurityDay]:
    base_path = Path(data_dir)
    profiles = _load_profiles(base_path / "profiles.csv")
    snapshots = _load_snapshots(base_path / "snapshots.csv")
    bars = _load_bars(base_path / "bars.csv")
    profile_order = {symbol: index for index, symbol in enumerate(profiles)}

    trading_keys = sorted(set(snapshots) | set(bars), key=lambda item: (item[1], profile_order.get(item[0], len(profile_order)), item[0]))
    securities: list[SecurityDay] = []
    for symbol, trading_day in trading_keys:
        profile = profiles.get(symbol)
        if profile is None:
            raise ValueError(f"Missing profile for symbol {symbol}")
        securities.append(
            SecurityDay(
                profile=profile,
                trading_day=trading_day,
                snapshots=snapshots.get((symbol, trading_day), {}),
                bars=sorted(bars.get((symbol, trading_day), []), key=lambda item: item.timestamp),
            )
        )
    return securities


def _load_profiles(path: Path) -> dict[str, InstrumentProfile]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            row["symbol"]: InstrumentProfile(
                symbol=row["symbol"],
                name=row["name"],
                stock_connect_eligible=_parse_bool(row["stock_connect_eligible"]),
                float_market_cap_hkd=float(row["float_market_cap_hkd"]),
                avg_turnover_20d_hkd=float(row["avg_turnover_20d_hkd"]),
                rsi_60m=float(row["rsi_60m"]),
                has_negative_announcement=_parse_bool(row.get("has_negative_announcement", "false")),
            )
            for row in reader
        }


def _load_snapshots(path: Path) -> dict[tuple[str, date], dict[str, SampleSnapshot]]:
    grouped: dict[tuple[str, date], dict[str, SampleSnapshot]] = defaultdict(dict)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trading_day = datetime.strptime(row["trading_day"], "%Y-%m-%d").date()
            key = (row["symbol"], trading_day)
            grouped[key][row["sample_time"]] = SampleSnapshot(
                sample_time=row["sample_time"],
                last_price=float(row["last_price"]),
                auction_change_pct=float(row["auction_change_pct"]),
                intraday_change_pct=float(row["intraday_change_pct"]),
                speed_3m_change_pct=float(row["speed_3m_change_pct"]),
                speed_3m_rank=int(row["speed_3m_rank"]),
                volume_ratio=float(row["volume_ratio"]),
                volume_ratio_rank=int(row["volume_ratio_rank"]),
                block_buy_ratio=float(row["block_buy_ratio"]),
                ask_bid_notional_ratio=float(row["ask_bid_notional_ratio"]),
                southbound_net_buy_ratio=float(row["southbound_net_buy_ratio"]),
                spread_pct=float(row["spread_pct"]),
                vwap=float(row["vwap"]),
                post_open_peak_gain_pct=float(row["post_open_peak_gain_pct"]),
            )
    return dict(grouped)


def _load_bars(path: Path) -> dict[tuple[str, date], list[PriceBar]]:
    grouped: dict[tuple[str, date], list[PriceBar]] = defaultdict(list)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
            key = (row["symbol"], timestamp.date())
            grouped[key].append(
                PriceBar(
                    timestamp=timestamp,
                    price=float(row["price"]),
                    vwap=float(row["vwap"]),
                    spread_pct=float(row["spread_pct"]),
                    intraday_gain_pct=float(row["intraday_gain_pct"]),
                    post_open_peak_gain_pct=float(row["post_open_peak_gain_pct"]),
                    ask_bid_notional_ratio=float(row.get("ask_bid_notional_ratio", 1.0)),
                    hang_seng_change_pct=float(row.get("hang_seng_change_pct", 0.0)),
                    hs300_change_pct=float(row.get("hs300_change_pct", 0.0)),
                    triggered_vcm=_parse_bool(row.get("triggered_vcm", "false")),
                    black_swan_event=_parse_bool(row.get("black_swan_event", "false")),
                )
            )
    return dict(grouped)


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}
