from __future__ import annotations

import argparse
from pathlib import Path

from .app import serve
from .backtest import BacktestEngine
from .data_loader import load_market_data
from .demo import build_demo_dataset
from .reporting import render_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="港股通T0动量策略回测与可视化系统")
    parser.add_argument("--serve", action="store_true", help="启动本地可视化仪表盘")
    parser.add_argument("--host", default="127.0.0.1", help="仪表盘监听地址")
    parser.add_argument("--port", type=int, default=8000, help="仪表盘端口")
    parser.add_argument("--output", type=Path, help="将仪表盘导出为 HTML 文件")
    parser.add_argument("--data-dir", type=Path, help="从指定目录加载真实 CSV 数据（profiles/snapshots/bars）")
    args = parser.parse_args()

    engine = BacktestEngine()
    dataset = load_market_data(args.data_dir) if args.data_dir else build_demo_dataset()
    result = engine.run(dataset)

    if args.output:
        args.output.write_text(render_dashboard(result), encoding="utf-8")
        print(f"Dashboard written to {args.output}")
    if args.serve:
        serve(args.host, args.port)
    elif not args.output:
        print(render_dashboard(result))


if __name__ == "__main__":
    main()
