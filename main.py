import argparse

import backtrader as bt

from datasource import fetch_bt_dataframe
from strategy import SmaCrossWithRiskStrategy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A compact Backtrader learning project using Tushare daily data."
    )
    parser.add_argument("--ts-code", default="000001.SZ", help="Tushare symbol.")
    parser.add_argument("--start-date", default="20200101", help="YYYYMMDD.")
    parser.add_argument("--end-date", default="20250101", help="YYYYMMDD.")
    parser.add_argument(
        "--adjust",
        choices=["none", "qfq", "hfq"],
        default="hfq",
        help="Price adjustment mode.",
    )
    parser.add_argument("--cash", type=float, default=100000.0, help="Initial cash.")
    parser.add_argument(
        "--commission",
        type=float,
        default=0.001,
        help="Broker commission ratio, e.g. 0.001 for 0.1%%.",
    )
    parser.add_argument(
        "--slippage",
        type=float,
        default=0.0,
        help="Percent slippage, e.g. 0.001 for 0.1%%.",
    )
    parser.add_argument("--fast-period", type=int, default=10, help="Fast SMA period.")
    parser.add_argument("--slow-period", type=int, default=30, help="Slow SMA period.")
    parser.add_argument("--atr-period", type=int, default=14, help="ATR period.")
    parser.add_argument(
        "--position-pct",
        type=float,
        default=0.95,
        help="Portfolio percentage used for each entry.",
    )
    parser.add_argument(
        "--stop-loss-atr",
        type=float,
        default=2.0,
        help="Stop-loss distance measured in ATR.",
    )
    parser.add_argument(
        "--take-profit-atr",
        type=float,
        default=4.0,
        help="Take-profit distance measured in ATR.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Optional Tushare token. If omitted, TUSHARE_TOKEN is used.",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Plot result after the backtest finishes.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable strategy log output.",
    )
    return parser


def build_cerebro(args: argparse.Namespace) -> tuple[bt.Cerebro, object]:
    if args.fast_period >= args.slow_period:
        raise ValueError("fast-period must be smaller than slow-period.")
    if not 0 < args.position_pct <= 1:
        raise ValueError("position-pct must be in (0, 1].")

    bt_df = fetch_bt_dataframe(
        ts_code=args.ts_code,
        start_date=args.start_date,
        end_date=args.end_date,
        adjust=args.adjust,
        token=args.token,
    )

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(
        SmaCrossWithRiskStrategy,
        fast_period=args.fast_period,
        slow_period=args.slow_period,
        atr_period=args.atr_period,
        position_pct=args.position_pct,
        stop_loss_atr=args.stop_loss_atr,
        take_profit_atr=args.take_profit_atr,
        print_log=not args.no_log,
    )
    cerebro.adddata(bt.feeds.PandasData(dataname=bt_df, name=args.ts_code))

    cerebro.broker.setcash(args.cash)
    cerebro.broker.setcommission(commission=args.commission)
    if args.slippage > 0:
        cerebro.broker.set_slippage_perc(perc=args.slippage)

    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.BuySell)
    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.DrawDown)

    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", annualize=True)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    return cerebro, bt_df


def nested_get(mapping, *keys, default=None):
    current = mapping
    for key in keys:
        if current is None:
            return default
        if hasattr(current, "get"):
            current = current.get(key)
        else:
            return default
    return current if current is not None else default


def safe_number(value, default=0.0):
    return default if value is None else value


def print_summary(strategy: bt.Strategy, args: argparse.Namespace, bt_df) -> None:
    returns = strategy.analyzers.returns.get_analysis()
    drawdown = strategy.analyzers.drawdown.get_analysis()
    sharpe = strategy.analyzers.sharpe.get_analysis()
    trades = strategy.analyzers.trades.get_analysis()

    total_closed = nested_get(trades, "total", "closed", default=0)
    total_won = nested_get(trades, "won", "total", default=0)
    total_lost = nested_get(trades, "lost", "total", default=0)
    net_pnl = safe_number(nested_get(trades, "pnl", "net", "total", default=0.0))
    max_drawdown = safe_number(
        nested_get(drawdown, "max", "drawdown", default=0.0)
    )
    annual_return = safe_number(returns.get("rnorm100", 0.0))
    total_return = safe_number(returns.get("rtot", 0.0)) * 100
    sharpe_ratio = safe_number(sharpe.get("sharperatio", 0.0))

    print("\n=== Backtest Summary ===")
    print(f"Symbol: {args.ts_code}")
    print(f"Bars: {len(bt_df)}")
    print(f"Range: {bt_df.index.min().date()} -> {bt_df.index.max().date()}")
    print(f"Starting Value: {args.cash:.2f}")
    print(f"Final Value: {strategy.broker.getvalue():.2f}")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Annualized Return: {annual_return:.2f}%")
    print(f"Max Drawdown: {max_drawdown:.2f}%")
    print(f"Sharpe Ratio: {sharpe_ratio:.4f}")
    print(f"Closed Trades: {total_closed}")
    print(f"Winning Trades: {total_won}")
    print(f"Losing Trades: {total_lost}")
    print(f"Net PnL: {net_pnl:.2f}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cerebro, bt_df = build_cerebro(args)
    print(
        f"Loading {args.ts_code} from {args.start_date} to {args.end_date}, "
        f"adjust={args.adjust}, bars={len(bt_df)}"
    )
    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")

    results = cerebro.run()
    strategy = results[0]
    print_summary(strategy, args, bt_df)

    if args.plot:
        cerebro.plot(style="candlestick")


if __name__ == "__main__":
    main()
