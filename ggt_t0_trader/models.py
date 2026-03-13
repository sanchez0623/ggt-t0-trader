from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List

MORNING_SAMPLING_TIMES = (
    "09:20",
    "09:25",
    "09:28",
    "09:32",
    "09:34",
    "09:36",
    "09:38",
    "09:40",
)
MIDDAY_SAMPLING_TIMES = ("13:00", "13:05")
ALL_SAMPLING_TIMES = MORNING_SAMPLING_TIMES + MIDDAY_SAMPLING_TIMES


@dataclass(frozen=True)
class InstrumentProfile:
    symbol: str
    name: str
    stock_connect_eligible: bool
    float_market_cap_hkd: float
    avg_turnover_20d_hkd: float
    rsi_60m: float
    has_negative_announcement: bool = False


@dataclass(frozen=True)
class SampleSnapshot:
    sample_time: str
    last_price: float
    auction_change_pct: float
    intraday_change_pct: float
    speed_3m_change_pct: float
    speed_3m_rank: int
    volume_ratio: float
    volume_ratio_rank: int
    block_buy_ratio: float
    ask_bid_notional_ratio: float
    southbound_net_buy_ratio: float
    spread_pct: float
    vwap: float
    post_open_peak_gain_pct: float


@dataclass(frozen=True)
class PriceBar:
    timestamp: datetime
    price: float
    vwap: float
    spread_pct: float
    intraday_gain_pct: float
    post_open_peak_gain_pct: float
    ask_bid_notional_ratio: float = 1.0
    hang_seng_change_pct: float = 0.0
    hs300_change_pct: float = 0.0
    triggered_vcm: bool = False
    black_swan_event: bool = False


@dataclass
class SecurityDay:
    profile: InstrumentProfile
    trading_day: date
    snapshots: Dict[str, SampleSnapshot]
    bars: List[PriceBar] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateScore:
    symbol: str
    name: str
    total_score: float
    appearance_score: float
    volume_rank_score: float
    speed_rank_score: float
    block_buy_score: float
    southbound_score: float
    appearances: int
    qualifying_times: List[str]
    average_volume_ratio_rank: float
    average_speed_rank: float
    average_block_buy_ratio: float
    average_southbound_net_buy_ratio: float


@dataclass(frozen=True)
class PortfolioSelection:
    positions: List[CandidateScore]
    per_position_weight: float
    total_weight: float


@dataclass(frozen=True)
class ExitEvent:
    timestamp: datetime
    price: float
    fraction: float
    reason: str


@dataclass
class Trade:
    symbol: str
    name: str
    entry_time: datetime
    entry_price: float
    allocation: float
    quantity: float
    exit_events: List[ExitEvent] = field(default_factory=list)

    @property
    def remaining_fraction(self) -> float:
        sold_fraction = sum(event.fraction for event in self.exit_events)
        return max(0.0, 1.0 - sold_fraction)

    @property
    def exit_time(self) -> datetime:
        return self.exit_events[-1].timestamp if self.exit_events else self.entry_time

    @property
    def realized_amount(self) -> float:
        return sum(self.quantity * event.fraction * event.price for event in self.exit_events)

    @property
    def cost_amount(self) -> float:
        return self.quantity * self.entry_price

    @property
    def pnl_amount(self) -> float:
        return self.realized_amount - self.cost_amount

    @property
    def pnl_pct(self) -> float:
        if not self.cost_amount:
            return 0.0
        return self.pnl_amount / self.cost_amount * 100

    @property
    def exit_reason(self) -> str:
        return self.exit_events[-1].reason if self.exit_events else "open"


@dataclass(frozen=True)
class PerformanceMetrics:
    total_return_pct: float
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: int


@dataclass(frozen=True)
class TargetEvaluation:
    win_rate_ok: bool
    profit_factor_ok: bool
    max_drawdown_ok: bool
    sharpe_ok: bool


@dataclass(frozen=True)
class BacktestResult:
    initial_capital: float
    ending_capital: float
    selection: PortfolioSelection
    midday_selection: PortfolioSelection
    trades: List[Trade]
    metrics: PerformanceMetrics
    targets: TargetEvaluation
    equity_curve: List[tuple[datetime, float]]
