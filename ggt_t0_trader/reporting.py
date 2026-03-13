from __future__ import annotations

from datetime import datetime
from html import escape

from .models import BacktestResult, CandidateScore


def _currency(value: float) -> str:
    return f"HK${value:,.0f}"


def _pct(value: float) -> str:
    return f"{value:.2f}%"


def _equity_svg(result: BacktestResult) -> str:
    if not result.equity_curve:
        return "<svg viewBox='0 0 800 240'><text x='20' y='120'>暂无权益曲线</text></svg>"
    values = [result.initial_capital] + [point[1] for point in result.equity_curve]
    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 1)
    points = []
    for index, (_, equity) in enumerate(result.equity_curve, start=1):
        x = 40 + (index - 1) * (700 / max(len(result.equity_curve) - 1, 1))
        y = 200 - ((equity - min_value) / span * 150)
        points.append(f"{x:.1f},{y:.1f}")
    baseline = 200 - ((result.initial_capital - min_value) / span * 150)
    labels = "".join(
        f"<text x='{40 + i * (700 / max(len(result.equity_curve) - 1, 1)):.1f}' y='225' font-size='11'>{escape(ts.strftime('%H:%M'))}</text>"
        for i, (ts, _) in enumerate(result.equity_curve)
    )
    return f"""
    <svg viewBox='0 0 800 240' role='img' aria-label='权益曲线'>
      <line x1='40' y1='{baseline:.1f}' x2='760' y2='{baseline:.1f}' stroke='#94a3b8' stroke-dasharray='4 4'/>
      <polyline fill='none' stroke='#0f766e' stroke-width='4' points='{' '.join(points)}'/>
      <text x='40' y='25' font-size='12'>初始资金：{_currency(result.initial_capital)}</text>
      <text x='40' y='42' font-size='12'>期末资金：{_currency(result.ending_capital)}</text>
      {labels}
    </svg>
    """


def _selection_rows(candidates: list[CandidateScore]) -> str:
    return "".join(
        "<tr>"
        f"<td>{escape(candidate.symbol)}</td>"
        f"<td>{escape(candidate.name)}</td>"
        f"<td>{candidate.total_score:.2f}</td>"
        f"<td>{candidate.appearances}</td>"
        f"<td>{candidate.average_volume_ratio_rank:.2f}</td>"
        f"<td>{candidate.average_speed_rank:.2f}</td>"
        f"<td>{candidate.average_block_buy_ratio:.2f}%</td>"
        f"<td>{candidate.average_southbound_net_buy_ratio:.2f}%</td>"
        "</tr>"
        for candidate in candidates
    )


def _trade_rows(result: BacktestResult) -> str:
    rows = []
    for trade in result.trades:
        exits = "<br/>".join(
            f"{exit_event.timestamp.strftime('%H:%M')} · {exit_event.reason} · {exit_event.fraction * 100:.0f}% @ {exit_event.price:.2f}"
            for exit_event in trade.exit_events
        )
        rows.append(
            "<tr>"
            f"<td>{escape(trade.symbol)}</td>"
            f"<td>{trade.entry_time.strftime('%H:%M')}</td>"
            f"<td>{trade.entry_price:.2f}</td>"
            f"<td>{_currency(trade.allocation)}</td>"
            f"<td>{exits}</td>"
            f"<td>{trade.exit_reason}</td>"
            f"<td>{_pct(trade.pnl_pct)}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_dashboard(result: BacktestResult) -> str:
    target_badges = [
        ("胜率≥55%", result.targets.win_rate_ok),
        ("盈亏比≥1.5", result.targets.profit_factor_ok),
        ("最大回撤≤10%", result.targets.max_drawdown_ok),
        ("夏普≥2", result.targets.sharpe_ok),
    ]
    badges_html = "".join(
        f"<span class='badge {'ok' if ok else 'warn'}'>{label}</span>" for label, ok in target_badges
    )
    return f"""
<!DOCTYPE html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>港股通T0动量策略可视化回测</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f8fafc; color: #0f172a; }}
    header {{ background: linear-gradient(135deg, #0f766e, #1d4ed8); color: white; padding: 32px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
    .card {{ background: white; border-radius: 16px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); padding: 20px; margin-bottom: 20px; }}
    .metric {{ font-size: 28px; font-weight: 700; margin: 8px 0 0; }}
    .label {{ color: #475569; font-size: 14px; }}
    .badge {{ display: inline-block; padding: 6px 10px; border-radius: 999px; margin-right: 8px; font-size: 13px; }}
    .badge.ok {{ background: #dcfce7; color: #166534; }}
    .badge.warn {{ background: #fee2e2; color: #991b1b; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; border-bottom: 1px solid #e2e8f0; padding: 12px 8px; vertical-align: top; }}
    .section-title {{ margin: 0 0 12px; }}
    .sampling {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
    .sampling span {{ background: #e2e8f0; padding: 6px 10px; border-radius: 999px; font-size: 13px; }}
    .small {{ color: #64748b; font-size: 13px; }}
  </style>
</head>
<body>
  <header>
    <h1>港股通日内 T0 动量策略仪表盘</h1>
    <p>双阶段采样、相对强度筛选、量化打分、风控执行、回测指标联动展示。</p>
    <div class='sampling'>
      <span>集合竞价：09:20 / 09:25 / 09:28</span>
      <span>稳定期：09:32 / 09:34 / 09:36 / 09:38 / 09:40</span>
      <span>午盘补充：13:00 / 13:05</span>
    </div>
  </header>
  <main>
    <section class='grid'>
      <div class='card'><div class='label'>总收益</div><div class='metric'>{_pct(result.metrics.total_return_pct)}</div></div>
      <div class='card'><div class='label'>胜率</div><div class='metric'>{_pct(result.metrics.win_rate_pct)}</div></div>
      <div class='card'><div class='label'>盈亏比</div><div class='metric'>{result.metrics.profit_factor:.2f}</div></div>
      <div class='card'><div class='label'>最大回撤</div><div class='metric'>{_pct(result.metrics.max_drawdown_pct)}</div></div>
      <div class='card'><div class='label'>夏普比率</div><div class='metric'>{result.metrics.sharpe_ratio:.2f}</div></div>
      <div class='card'><div class='label'>交易笔数</div><div class='metric'>{result.metrics.trades}</div></div>
    </section>

    <section class='card'>
      <h2 class='section-title'>回测达标检查</h2>
      {badges_html}
      <p class='small'>资金分配：单票 {result.selection.per_position_weight * 100:.0f}% 上限，总仓位 {result.selection.total_weight * 100:.0f}% 。</p>
      {_equity_svg(result)}
    </section>

    <section class='card'>
      <h2 class='section-title'>9:40 选股结果</h2>
      <table>
        <thead>
          <tr><th>代码</th><th>名称</th><th>总分</th><th>出现次数</th><th>平均量比排名</th><th>平均涨速排名</th><th>平均大单买入占比</th><th>港股通净买入占比</th></tr>
        </thead>
        <tbody>{_selection_rows(result.selection.positions)}</tbody>
      </table>
    </section>

    <section class='card'>
      <h2 class='section-title'>13:00 午盘补充候选</h2>
      <table>
        <thead>
          <tr><th>代码</th><th>名称</th><th>总分</th><th>出现次数</th><th>平均量比排名</th><th>平均涨速排名</th><th>平均大单买入占比</th><th>港股通净买入占比</th></tr>
        </thead>
        <tbody>{_selection_rows(result.midday_selection.positions)}</tbody>
      </table>
    </section>

    <section class='card'>
      <h2 class='section-title'>交易执行与风控明细</h2>
      <table>
        <thead>
          <tr><th>代码</th><th>入场时间</th><th>入场价</th><th>分配资金</th><th>退出事件</th><th>最终原因</th><th>收益率</th></tr>
        </thead>
        <tbody>{_trade_rows(result)}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""
