from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, List

from .models import (
    MIDDAY_SAMPLING_TIMES,
    MORNING_SAMPLING_TIMES,
    CandidateScore,
    PortfolioSelection,
    SampleSnapshot,
    SecurityDay,
)


@dataclass(frozen=True)
class StrategyConfig:
    min_float_market_cap_hkd: float = 5_000_000_000
    max_float_market_cap_hkd: float = 50_000_000_000
    min_avg_turnover_20d_hkd: float = 30_000_000
    min_rsi_60m: float = 50.0
    min_volume_ratio: float = 2.0
    min_auction_change_pct: float = 0.5
    max_auction_change_pct: float = 5.0
    min_block_buy_ratio: float = 60.0
    max_ask_bid_notional_ratio: float = 1.5
    min_southbound_net_buy_ratio: float = 10.0
    max_speed_rank: int = 30
    max_positions: int = 5
    min_positions: int = 3
    max_position_weight: float = 0.2
    max_total_weight: float = 0.8


class HongKongT0MomentumStrategy:
    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig()

    def profile_passes(self, security_day: SecurityDay) -> bool:
        profile = security_day.profile
        return all(
            [
                profile.stock_connect_eligible,
                self.config.min_float_market_cap_hkd <= profile.float_market_cap_hkd <= self.config.max_float_market_cap_hkd,
                profile.avg_turnover_20d_hkd >= self.config.min_avg_turnover_20d_hkd,
                profile.rsi_60m >= self.config.min_rsi_60m,
                not profile.has_negative_announcement,
            ]
        )

    def snapshot_passes(self, sample_time: str, snapshot: SampleSnapshot) -> bool:
        if snapshot.volume_ratio < self.config.min_volume_ratio:
            return False
        if snapshot.speed_3m_rank > self.config.max_speed_rank:
            return False
        if snapshot.block_buy_ratio < self.config.min_block_buy_ratio:
            return False
        if snapshot.ask_bid_notional_ratio > self.config.max_ask_bid_notional_ratio:
            return False
        if snapshot.southbound_net_buy_ratio < self.config.min_southbound_net_buy_ratio:
            return False
        if sample_time in MORNING_SAMPLING_TIMES[:3]:
            return self.config.min_auction_change_pct <= snapshot.auction_change_pct <= self.config.max_auction_change_pct
        return snapshot.intraday_change_pct >= 0.0

    def screen_candidates(self, universe: Iterable[SecurityDay], sample_time: str) -> List[SecurityDay]:
        candidates = []
        for security_day in universe:
            if not self.profile_passes(security_day):
                continue
            snapshot = security_day.snapshots.get(sample_time)
            if snapshot and self.snapshot_passes(sample_time, snapshot):
                candidates.append(security_day)
        return candidates

    def _rank_score(self, average_rank: float, max_score: float) -> float:
        capped_rank = min(max(average_rank, 1.0), float(self.config.max_speed_rank))
        relative = (self.config.max_speed_rank + 1 - capped_rank) / self.config.max_speed_rank
        return round(relative * max_score, 2)

    def _block_buy_score(self, average_ratio: float) -> float:
        if average_ratio < self.config.min_block_buy_ratio:
            return 0.0
        score = 10.0 + max(0.0, (average_ratio - self.config.min_block_buy_ratio) // 5)
        return round(min(15.0, score), 2)

    def _southbound_score(self, average_ratio: float) -> float:
        if average_ratio < self.config.min_southbound_net_buy_ratio:
            return 0.0
        score = 5.0 + max(0.0, (average_ratio - self.config.min_southbound_net_buy_ratio) // 5)
        return round(min(10.0, score), 2)

    def _score_for_times(self, universe: Iterable[SecurityDay], sampling_times: tuple[str, ...]) -> List[CandidateScore]:
        qualified = {}
        for sample_time in sampling_times:
            for security_day in self.screen_candidates(universe, sample_time):
                record = qualified.setdefault(
                    security_day.profile.symbol,
                    {
                        "security_day": security_day,
                        "times": [],
                        "volume_ranks": [],
                        "speed_ranks": [],
                        "block_buy": [],
                        "southbound": [],
                    },
                )
                snapshot = security_day.snapshots[sample_time]
                record["times"].append(sample_time)
                record["volume_ranks"].append(snapshot.volume_ratio_rank)
                record["speed_ranks"].append(snapshot.speed_3m_rank)
                record["block_buy"].append(snapshot.block_buy_ratio)
                record["southbound"].append(snapshot.southbound_net_buy_ratio)

        scores = []
        total_slots = len(sampling_times) or 1
        for symbol, record in qualified.items():
            appearances = len(record["times"])
            average_volume_ratio_rank = mean(record["volume_ranks"])
            average_speed_rank = mean(record["speed_ranks"])
            average_block_buy_ratio = mean(record["block_buy"])
            average_southbound_ratio = mean(record["southbound"])

            appearance_score = round(appearances / total_slots * 30.0, 2)
            volume_rank_score = self._rank_score(average_volume_ratio_rank, 20.0)
            speed_rank_score = self._rank_score(average_speed_rank, 25.0)
            block_buy_score = self._block_buy_score(average_block_buy_ratio)
            southbound_score = self._southbound_score(average_southbound_ratio)
            total_score = round(
                appearance_score + volume_rank_score + speed_rank_score + block_buy_score + southbound_score,
                2,
            )
            security_day = record["security_day"]
            scores.append(
                CandidateScore(
                    symbol=symbol,
                    name=security_day.profile.name,
                    total_score=total_score,
                    appearance_score=appearance_score,
                    volume_rank_score=volume_rank_score,
                    speed_rank_score=speed_rank_score,
                    block_buy_score=block_buy_score,
                    southbound_score=southbound_score,
                    appearances=appearances,
                    qualifying_times=record["times"],
                    average_volume_ratio_rank=round(average_volume_ratio_rank, 2),
                    average_speed_rank=round(average_speed_rank, 2),
                    average_block_buy_ratio=round(average_block_buy_ratio, 2),
                    average_southbound_net_buy_ratio=round(average_southbound_ratio, 2),
                )
            )
        return sorted(scores, key=lambda item: (-item.total_score, item.average_speed_rank, item.symbol))

    def score_morning_candidates(self, universe: Iterable[SecurityDay]) -> List[CandidateScore]:
        return self._score_for_times(universe, MORNING_SAMPLING_TIMES)

    def score_midday_candidates(self, universe: Iterable[SecurityDay]) -> List[CandidateScore]:
        return self._score_for_times(universe, MIDDAY_SAMPLING_TIMES)

    def build_portfolio(self, scored_candidates: List[CandidateScore]) -> PortfolioSelection:
        if not scored_candidates:
            return PortfolioSelection(positions=[], per_position_weight=0.0, total_weight=0.0)
        desired_positions = min(self.config.max_positions, max(self.config.min_positions, len(scored_candidates)))
        selected = scored_candidates[:desired_positions]
        per_position_weight = min(self.config.max_position_weight, self.config.max_total_weight / len(selected))
        total_weight = round(per_position_weight * len(selected), 4)
        return PortfolioSelection(
            positions=selected,
            per_position_weight=round(per_position_weight, 4),
            total_weight=total_weight,
        )

    def should_open_position(self, snapshot: SampleSnapshot) -> bool:
        if snapshot.spread_pct > 0.2:
            return False
        if snapshot.last_price <= 0 or snapshot.vwap <= 0:
            return False
        near_vwap = abs(snapshot.last_price - snapshot.vwap) / snapshot.vwap <= 0.005
        pullback = max(0.0, snapshot.post_open_peak_gain_pct - snapshot.intraday_change_pct)
        within_pullback_limit = pullback <= max(snapshot.post_open_peak_gain_pct * 0.5, 0.5)
        return near_vwap or within_pullback_limit
