from __future__ import annotations

from datetime import date, datetime

from .models import InstrumentProfile, PriceBar, SampleSnapshot, SecurityDay


def _snapshot(
    sample_time: str,
    last_price: float,
    auction_change_pct: float,
    intraday_change_pct: float,
    speed_rank: int,
    volume_ratio: float,
    volume_rank: int,
    block_buy_ratio: float,
    ask_bid_ratio: float,
    southbound_ratio: float,
    spread_pct: float,
    vwap: float,
    peak_gain_pct: float,
) -> SampleSnapshot:
    return SampleSnapshot(
        sample_time=sample_time,
        last_price=last_price,
        auction_change_pct=auction_change_pct,
        intraday_change_pct=intraday_change_pct,
        speed_3m_change_pct=intraday_change_pct,
        speed_3m_rank=speed_rank,
        volume_ratio=volume_ratio,
        volume_ratio_rank=volume_rank,
        block_buy_ratio=block_buy_ratio,
        ask_bid_notional_ratio=ask_bid_ratio,
        southbound_net_buy_ratio=southbound_ratio,
        spread_pct=spread_pct,
        vwap=vwap,
        post_open_peak_gain_pct=peak_gain_pct,
    )


def _bars(base_date: date, rows: list[tuple[str, float, float, float, float, float, bool, bool]]) -> list[PriceBar]:
    bars = []
    for ts, price, vwap, intraday_gain, peak_gain, ask_bid_ratio, triggered_vcm, black_swan in rows:
        hour, minute = [int(part) for part in ts.split(":")]
        bars.append(
            PriceBar(
                timestamp=datetime(base_date.year, base_date.month, base_date.day, hour, minute),
                price=price,
                vwap=vwap,
                spread_pct=0.12,
                intraday_gain_pct=intraday_gain,
                post_open_peak_gain_pct=peak_gain,
                ask_bid_notional_ratio=ask_bid_ratio,
                hang_seng_change_pct=-0.3,
                hs300_change_pct=-0.1,
                triggered_vcm=triggered_vcm,
                black_swan_event=black_swan,
            )
        )
    return bars


def build_demo_dataset() -> list[SecurityDay]:
    trading_day = date(2026, 3, 13)
    morning = {
        "09:20": (1.2, 1.2, 2.8, 2, 78, 1.2, 18),
        "09:25": (1.5, 1.5, 3.1, 1, 80, 1.1, 19),
        "09:28": (1.8, 1.8, 3.4, 2, 82, 1.0, 20),
        "09:32": (2.1, 2.1, 3.6, 3, 76, 1.2, 18),
        "09:34": (2.4, 2.4, 3.5, 2, 77, 1.1, 19),
        "09:36": (2.9, 2.9, 3.8, 2, 79, 1.1, 21),
        "09:38": (3.2, 3.2, 4.0, 1, 81, 1.0, 20),
        "09:40": (3.0, 3.0, 3.7, 2, 80, 1.2, 18),
        "13:00": (3.5, 3.5, 4.3, 3, 76, 1.2, 22),
        "13:05": (3.8, 3.8, 4.5, 2, 78, 1.1, 23),
    }
    profiles = [
        InstrumentProfile("02201.HK", "Alpha Mobility", True, 18_000_000_000, 58_000_000, 57),
        InstrumentProfile("03988.HK", "Beta Health", True, 12_000_000_000, 42_000_000, 55),
        InstrumentProfile("06618.HK", "Gamma Cloud", True, 26_000_000_000, 71_000_000, 61),
        InstrumentProfile("01288.HK", "Delta Retail", True, 9_000_000_000, 35_000_000, 53),
        InstrumentProfile("09977.HK", "Excluded MegaCap", True, 80_000_000_000, 120_000_000, 62),
    ]

    securities: list[SecurityDay] = []
    for index, profile in enumerate(profiles):
        snapshots = {}
        for sample_time, (auction_pct, intraday_pct, volume_ratio, speed_rank, block_buy, ask_bid_ratio, southbound) in morning.items():
            penalty = index * 3
            snapshots[sample_time] = _snapshot(
                sample_time=sample_time,
                last_price=10 + index + intraday_pct / 10,
                auction_change_pct=max(0.2, auction_pct - index * 0.2),
                intraday_change_pct=max(-0.5, intraday_pct - index * 0.3),
                speed_rank=speed_rank + penalty,
                volume_ratio=max(1.2, volume_ratio - index * 0.25),
                volume_rank=min(30, 1 + index + (0 if speed_rank < 3 else 2)),
                block_buy_ratio=max(48, block_buy - index * 4),
                ask_bid_ratio=min(1.8, ask_bid_ratio + index * 0.15),
                southbound_ratio=max(4, southbound - index * 3),
                spread_pct=0.12 + index * 0.02,
                vwap=10 + index + intraday_pct / 10 - 0.04,
                peak_gain_pct=max(1.0, intraday_pct + 0.8),
            )
        bars_map = {
            "02201.HK": _bars(
                trading_day,
                [
                    ("09:42", 10.35, 10.32, 2.8, 3.6, 1.1, False, False),
                    ("10:10", 10.68, 10.50, 3.4, 3.8, 1.0, False, False),
                    ("10:25", 10.90, 10.74, 5.2, 5.4, 1.0, False, False),
                ],
            ),
            "03988.HK": _bars(
                trading_day,
                [
                    ("09:44", 11.10, 11.06, 2.1, 2.7, 1.2, False, False),
                    ("10:03", 10.84, 10.98, -2.3, 2.7, 1.4, False, False),
                ],
            ),
            "06618.HK": _bars(
                trading_day,
                [
                    ("09:47", 12.18, 12.15, 1.8, 2.1, 1.2, False, False),
                    ("10:49", 12.26, 12.20, 0.7, 2.2, 1.2, False, False),
                ],
            ),
            "01288.HK": _bars(
                trading_day,
                [
                    ("09:46", 13.04, 12.90, 1.5, 1.9, 1.65, False, False),
                    ("15:50", 13.30, 13.12, 2.0, 2.4, 1.2, False, False),
                ],
            ),
            "09977.HK": _bars(
                trading_day,
                [
                    ("09:41", 18.00, 17.96, 1.0, 1.4, 1.0, False, False),
                    ("10:15", 18.55, 18.20, 3.6, 3.8, 1.0, False, False),
                ],
            ),
        }
        securities.append(SecurityDay(profile=profile, trading_day=trading_day, snapshots=snapshots, bars=bars_map[profile.symbol]))

    return securities
