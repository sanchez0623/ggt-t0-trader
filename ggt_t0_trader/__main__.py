from __future__ import annotations

import argparse
from pathlib import Path

from .app import serve
from .backtest import BacktestEngine
from .demo import build_demo_dataset
from .reporting import render_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="港股通T0动量策略回测与可视化系统")
    parser.add_argument("--serve", action="store_true", help="启动本地可视化仪表盘")
    parser.add_argument("--host", default="127.0.0.1", help="仪表盘监听地址")
    parser.add_argument("--port", type=int, default=8000, help="仪表盘端口")
    parser.add_argument("--output", type=Path, help="将仪表盘导出为 HTML 文件")
    args = parser.parse_args()

    engine = BacktestEngine()
    result = engine.run(build_demo_dataset())

    if args.output:
        args.output.write_text(render_dashboard(result), encoding="utf-8")
        print(f"Dashboard written to {args.output}")
    if args.serve:
        serve(args.host, args.port)
    elif not args.output:
        print(render_dashboard(result))


if __name__ == "__main__":
    main()
