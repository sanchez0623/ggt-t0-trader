from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from math import inf, sqrt
from statistics import mean, pstdev
from typing import Iterable, List, Sequence

from .models import (
    BacktestResult,
    ExitEvent,
    PerformanceMetrics,
    PortfolioSelection,
    PriceBar,
    TargetEvaluation,
    Trade,
)
from .strategy import HongKongT0MomentumStrategy


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 1_000_000.0
    first_take_profit_pct: float = 3.0
    second_take_profit_pct: float = 5.0
    stop_loss_pct: float = -2.0
    trailing_stop_floor_pct: float = 1.0
    time_stop_hours: int = 1
    time_stop_min_gain_pct: float = 1.0
    force_exit_time: time = time(15, 50)
    entry_start_time: time = time(9, 40)
    entry_end_time: time = time(10, 0)
    max_hang_seng_drawdown_pct: float = -1.0
    max_hs300_drawdown_pct: float = -0.5


class BacktestEngine:
    def __init__(self, strategy: HongKongT0MomentumStrategy | None = None, config: BacktestConfig | None = None) -> None:
        self.strategy = strategy or HongKongT0MomentumStrategy()
        self.config = config or BacktestConfig()

    def run(self, universe: Sequence) -> BacktestResult:
        morning_scores = self.strategy.score_morning_candidates(universe)
        midday_scores = self.strategy.score_midday_candidates(universe)
        morning_selection = self.strategy.build_portfolio(morning_scores)
        midday_selection = self.strategy.build_portfolio(midday_scores)
        symbol_to_security = {security_day.profile.symbol: security_day for security_day in universe}

        trades: List[Trade] = []
        event_points: List[tuple[datetime, float]] = []
        available_capital = self.config.initial_capital
        allocated_capital = self.config.initial_capital * morning_selection.total_weight

        for candidate in morning_selection.positions:
            security_day = symbol_to_security[candidate.symbol]
            allocation = self.config.initial_capital * morning_selection.per_position_weight
            trade = self._simulate_trade(candidate.symbol, candidate.name, security_day.bars, allocation)
            if trade is None:
                continue
            available_capital += trade.pnl_amount
            trades.append(trade)
            cumulative_equity = self.config.initial_capital + sum(item.pnl_amount for item in trades)
            event_points.append((trade.exit_time, cumulative_equity))

        metrics = self._calculate_metrics(trades, event_points)
        targets = TargetEvaluation(
            win_rate_ok=metrics.win_rate_pct >= 55.0,
            profit_factor_ok=metrics.profit_factor >= 1.5,
            max_drawdown_ok=metrics.max_drawdown_pct <= 10.0,
            sharpe_ok=metrics.sharpe_ratio >= 2.0,
        )
        return BacktestResult(
            initial_capital=self.config.initial_capital,
            ending_capital=available_capital,
            selection=morning_selection,
            midday_selection=midday_selection,
            trades=trades,
            metrics=metrics,
            targets=targets,
            equity_curve=event_points,
        )

    def _market_risk_triggered(self, bar: PriceBar) -> bool:
        return (
            bar.hang_seng_change_pct <= self.config.max_hang_seng_drawdown_pct
            or bar.hs300_change_pct <= self.config.max_hs300_drawdown_pct
        )

    def _entry_snapshot_from_bar(self, bar: PriceBar):
        from .models import SampleSnapshot

        return SampleSnapshot(
            sample_time=bar.timestamp.strftime("%H:%M"),
            last_price=bar.price,
            auction_change_pct=0.0,
            intraday_change_pct=bar.intraday_gain_pct,
            speed_3m_change_pct=0.0,
            speed_3m_rank=1,
            volume_ratio=2.0,
            volume_ratio_rank=1,
            block_buy_ratio=60.0,
            ask_bid_notional_ratio=bar.ask_bid_notional_ratio,
            southbound_net_buy_ratio=10.0,
            spread_pct=bar.spread_pct,
            vwap=bar.vwap,
            post_open_peak_gain_pct=bar.post_open_peak_gain_pct,
        )

    def _simulate_trade(self, symbol: str, name: str, bars: Iterable[PriceBar], allocation: float) -> Trade | None:
        sorted_bars = sorted(bars, key=lambda item: item.timestamp)
        entry_bar = None
        trading_halted = False
        for bar in sorted_bars:
            if bar.black_swan_event or self._market_risk_triggered(bar):
                trading_halted = True
                break
            current_time = bar.timestamp.time()
            if not (self.config.entry_start_time <= current_time <= self.config.entry_end_time):
                continue
            if self.strategy.should_open_position(self._entry_snapshot_from_bar(bar)):
                entry_bar = bar
                break
        if trading_halted or entry_bar is None:
            return None

        quantity = allocation / entry_bar.price if entry_bar.price else 0.0
        if quantity <= 0:
            return None
        trade = Trade(
            symbol=symbol,
            name=name,
            entry_time=entry_bar.timestamp,
            entry_price=entry_bar.price,
            allocation=allocation,
            quantity=quantity,
        )

        first_take_profit_taken = False
        dynamic_stop_price = None
        time_stop_deadline = entry_bar.timestamp + timedelta(hours=self.config.time_stop_hours)

        for bar in sorted_bars:
            if bar.timestamp <= entry_bar.timestamp:
                continue
            gain_pct = (bar.price - entry_bar.price) / entry_bar.price * 100

            if bar.black_swan_event:
                self._exit_remaining(trade, bar, "black_swan_exit")
                break
            if bar.triggered_vcm and bar.ask_bid_notional_ratio > self.strategy.config.max_ask_bid_notional_ratio:
                self._exit_remaining(trade, bar, "vcm_exit")
                break
            if self._market_risk_triggered(bar):
                self._exit_remaining(trade, bar, "market_risk_exit")
                break
            if gain_pct <= self.config.stop_loss_pct:
                self._exit_remaining(trade, bar, "stop_loss")
                break
            if not first_take_profit_taken and gain_pct >= self.config.first_take_profit_pct:
                trade.exit_events.append(ExitEvent(timestamp=bar.timestamp, price=bar.price, fraction=0.5, reason="take_profit_3pct"))
                first_take_profit_taken = True
            if gain_pct >= self.config.second_take_profit_pct and trade.remaining_fraction > 0:
                trade.exit_events.append(
                    ExitEvent(timestamp=bar.timestamp, price=bar.price, fraction=trade.remaining_fraction, reason="take_profit_5pct")
                )
                break
            if gain_pct > self.config.second_take_profit_pct:
                dynamic_stop_price = max(dynamic_stop_price or 0.0, entry_bar.price * (1 + self.config.trailing_stop_floor_pct / 100))
            if dynamic_stop_price and bar.price <= dynamic_stop_price and trade.remaining_fraction > 0:
                trade.exit_events.append(
                    ExitEvent(timestamp=bar.timestamp, price=bar.price, fraction=trade.remaining_fraction, reason="dynamic_stop")
                )
                break
            if bar.timestamp >= time_stop_deadline and gain_pct < self.config.time_stop_min_gain_pct and trade.remaining_fraction > 0:
                trade.exit_events.append(
                    ExitEvent(timestamp=bar.timestamp, price=bar.price, fraction=trade.remaining_fraction, reason="time_stop")
                )
                break
            if bar.timestamp.time() >= self.config.force_exit_time and trade.remaining_fraction > 0:
                trade.exit_events.append(
                    ExitEvent(timestamp=bar.timestamp, price=bar.price, fraction=trade.remaining_fraction, reason="force_exit")
                )
                break

        if trade.remaining_fraction > 0 and sorted_bars:
            last_bar = sorted_bars[-1]
            trade.exit_events.append(
                ExitEvent(timestamp=last_bar.timestamp, price=last_bar.price, fraction=trade.remaining_fraction, reason="end_of_data_exit")
            )
        return trade

    def _exit_remaining(self, trade: Trade, bar: PriceBar, reason: str) -> None:
        if trade.remaining_fraction > 0:
            trade.exit_events.append(
                ExitEvent(timestamp=bar.timestamp, price=bar.price, fraction=trade.remaining_fraction, reason=reason)
            )

    def _calculate_metrics(self, trades: Sequence[Trade], equity_curve: Sequence[tuple[datetime, float]]) -> PerformanceMetrics:
        if not trades:
            return PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0)

        trade_returns = [trade.pnl_pct / 100 for trade in trades]
        gross_profit = sum(max(0.0, trade.pnl_amount) for trade in trades)
        gross_loss = sum(min(0.0, trade.pnl_amount) for trade in trades)
        win_rate = sum(1 for trade in trades if trade.pnl_amount > 0) / len(trades) * 100
        profit_factor = gross_profit / abs(gross_loss) if gross_loss else inf
        drawdown = self._max_drawdown(equity_curve)
        sharpe = 0.0
        if len(trade_returns) > 1 and pstdev(trade_returns) > 0:
            sharpe = mean(trade_returns) / pstdev(trade_returns) * sqrt(len(trade_returns))
        ending_capital = self.config.initial_capital + sum(trade.pnl_amount for trade in trades)
        total_return_pct = (ending_capital - self.config.initial_capital) / self.config.initial_capital * 100
        return PerformanceMetrics(
            total_return_pct=round(total_return_pct, 2),
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(profit_factor if profit_factor != inf else 999.0, 2),
            max_drawdown_pct=round(drawdown, 2),
            sharpe_ratio=round(sharpe, 2),
            trades=len(trades),
        )

    def _max_drawdown(self, equity_curve: Sequence[tuple[datetime, float]]) -> float:
        if not equity_curve:
            return 0.0
        peak = self.config.initial_capital
        max_drawdown = 0.0
        for _, equity in equity_curve:
            peak = max(peak, equity)
            if peak <= 0:
                continue
            drawdown = max(0.0, (peak - equity) / peak * 100)
            max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown
