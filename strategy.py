import math

import backtrader as bt


class SmaCrossWithRiskStrategy(bt.Strategy):
    params = dict(
        fast_period=10,
        slow_period=30,
        atr_period=14,
        position_pct=0.95,
        stop_loss_atr=2.0,
        take_profit_atr=4.0,
        print_log=True,
    )

    def log(self, txt: str, dt=None) -> None:
        if not self.p.print_log:
            return
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} | {txt}")

    def __init__(self) -> None:
        self.data_close = self.datas[0].close
        self.order = None
        self.entry_price = None
        self.stop_price = None
        self.take_profit_price = None

        self.fast_sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.p.fast_period
        )
        self.slow_sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.p.slow_period
        )
        self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)
        self.atr = bt.indicators.AverageTrueRange(
            self.datas[0], period=self.p.atr_period
        )

    def start(self) -> None:
        self.log(f"Strategy start, initial cash={self.broker.getcash():.2f}")

    def notify_order(self, order: bt.Order) -> None:
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.entry_price = order.executed.price
                atr_value = float(self.atr[0]) if math.isfinite(self.atr[0]) else 0.0
                self.stop_price = self.entry_price - atr_value * self.p.stop_loss_atr
                self.take_profit_price = (
                    self.entry_price + atr_value * self.p.take_profit_atr
                )
                self.log(
                    "BUY EXECUTED, "
                    f"price={order.executed.price:.2f}, "
                    f"size={order.executed.size:.0f}, "
                    f"cost={order.executed.value:.2f}, "
                    f"comm={order.executed.comm:.2f}, "
                    f"stop={self.stop_price:.2f}, "
                    f"take={self.take_profit_price:.2f}"
                )
            else:
                self.log(
                    "SELL EXECUTED, "
                    f"price={order.executed.price:.2f}, "
                    f"size={abs(order.executed.size):.0f}, "
                    f"value={order.executed.value:.2f}, "
                    f"comm={order.executed.comm:.2f}"
                )
                self.entry_price = None
                self.stop_price = None
                self.take_profit_price = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"ORDER FAILED, status={order.getstatusname()}")

        self.order = None

    def notify_trade(self, trade: bt.Trade) -> None:
        if not trade.isclosed:
            return
        self.log(
            f"TRADE CLOSED, gross_pnl={trade.pnl:.2f}, net_pnl={trade.pnlcomm:.2f}"
        )

    def next(self) -> None:
        warmup = max(self.p.slow_period, self.p.atr_period)
        if len(self) < warmup or self.order:
            return

        self.log(
            "close="
            f"{self.data_close[0]:.2f}, "
            f"fast_sma={self.fast_sma[0]:.2f}, "
            f"slow_sma={self.slow_sma[0]:.2f}, "
            f"position={self.position.size}"
        )

        if not self.position:
            if self.crossover > 0:
                cash = self.broker.getcash()
                size = int(cash * self.p.position_pct / self.data_close[0])
                if size > 0:
                    self.log(f"BUY CREATE, size={size}")
                    self.order = self.buy(size=size)
            return

        should_exit = False
        exit_reason = ""

        if self.crossover < 0:
            should_exit = True
            exit_reason = "dead cross"
        elif self.stop_price is not None and self.data_close[0] <= self.stop_price:
            should_exit = True
            exit_reason = "stop loss"
        elif (
            self.take_profit_price is not None
            and self.data_close[0] >= self.take_profit_price
        ):
            should_exit = True
            exit_reason = "take profit"

        if should_exit:
            self.log(f"CLOSE CREATE, reason={exit_reason}")
            self.order = self.close()

    def stop(self) -> None:
        self.log(
            "Strategy finished, "
            f"final value={self.broker.getvalue():.2f}, "
            f"cash={self.broker.getcash():.2f}"
        )
