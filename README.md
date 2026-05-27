# Backtrader API 学习项目

面向 [`backtrader`](https://www.backtrader.com/docu/) 入门与查阅。
更多说明可以查看https://backtrader-zh.readthedocs.io/zh-cn/latest/index_zh.html

## 1. 项目文件

```text
backtrader_learn/
├── datasource.py      # 拉取 Tushare 数据并整理为 PandasData 可用格式
├── strategy.py        # 示例策略，演示指标、信号、订单和交易回调
├── main.py            # 回测入口，组装 Cerebro 并输出分析结果
├── requirements.txt   # 依赖
└── README.md          # 项目说明与 Backtrader API 参考
```

## 2. 快速开始

### 2.1 安装依赖

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2.2 配置 Tushare Token

```powershell
$env:TUSHARE_TOKEN="你的 tushare token"
```

也可以运行时通过 `--token` 传入。

### 2.3 运行示例

```powershell
python main.py
```

带参数运行：

```powershell
python main.py `
  --ts-code 600519.SH `
  --start-date 20200101 `
  --end-date 20250101 `
  --adjust qfq `
  --cash 100000 `
  --commission 0.001 `
  --slippage 0.0005 `
  --fast-period 10 `
  --slow-period 30 `
  --plot
```

## 3. 项目在用什么 API

这个项目主要覆盖下面这些 `backtrader` 核心 API：

- `bt.Cerebro`
- `bt.Strategy`
- `bt.feeds.PandasData`
- `bt.indicators.*`
- `broker.setcash / setcommission / set_slippage_perc`
- `buy / sell / close / notify_order / notify_trade`
- `bt.observers.*`
- `bt.analyzers.*`

## 4. Backtrader API 总览

`backtrader` 的核心对象关系可以简化成下面这样：

```text
Data Feed --> Strategy --> Order / Trade
                 |
                 v
               Broker
                 |
                 v
      Observer / Analyzer / Plot
                 ^
                 |
              Cerebro
```

## 5. `bt.Cerebro` API

`Cerebro` 是回测引擎，也是绝大多数代码的入口对象。它负责注册策略、挂载数据、配置 Broker、运行回测、收集分析结果和画图。

### 5.1 常用构造方式

```python
cerebro = bt.Cerebro(stdstats=False)
```

本项目把 `stdstats=False` 打开，表示关闭默认观察器，改为手动添加自己需要的 `Observer`。

### 5.2 常用方法

```python
addstrategy(self, strategy, *args, **kwargs)
optstrategy(self, strategy, *args, **kwargs)
adddata(self, data, name=None)
resampledata(self, dataname, name=None, **kwargs)
replaydata(self, dataname, name=None, **kwargs)
addobserver(self, obscls, *args, **kwargs)
addanalyzer(self, ancls, *args, **kwargs)
addsizer(self, sizercls, *args, **kwargs)
run(self, **kwargs)
plot(self, plotter=None, numfigs=1, iplot=True, start=None, end=None, width=16,
     height=9, dpi=300, tight=True, use=None, **kwargs)
```

### 5.3 方法说明

| API            | 作用                                                 | 本项目是否使用 |
| -------------- | ---------------------------------------------------- | -------------- |
| `addstrategy`  | 注册一个策略类，`*args` 和 `**kwargs` 会传给策略参数 | 是             |
| `optstrategy`  | 注册参数优化任务，通常用于批量测试参数组合           | 否             |
| `adddata`      | 添加一个数据源                                       | 是             |
| `resampledata` | 把已有数据重采样为更大周期，例如分钟转日线           | 否             |
| `replaydata`   | 重放数据形成更高周期 Bar，适合观察 Bar 形成过程      | 否             |
| `addobserver`  | 注册图形观察器                                       | 是             |
| `addanalyzer`  | 注册分析器                                           | 是             |
| `addsizer`     | 注册统一仓位管理器                                   | 否             |
| `run`          | 启动回测                                             | 是             |
| `plot`         | 绘图                                                 | 是             |

### 5.4 `run()` 

普通回测时：

```python
results = cerebro.run()
strategy = results[0]
```

此时 `results` 通常是策略实例列表。

### 5.5 本项目怎么使用 `Cerebro`

`main.py` 里做了这几步：

1. 创建 `bt.Cerebro(stdstats=False)`
2. `addstrategy(SmaCrossWithRiskStrategy, ...)`
3. `adddata(bt.feeds.PandasData(...))`
4. `broker.setcash(...)`
5. `broker.setcommission(...)`
6. `broker.set_slippage_perc(...)`
7. `addobserver(...)`
8. `addanalyzer(...)`
9. `run()`
10. 从 `strategy.analyzers.xxx.get_analysis()` 读取结果

## 6. `bt.Strategy` API

`Strategy` 是策略的主体。你通常会继承 `bt.Strategy`，把指标定义、买卖信号、订单回调、交易回调都写在这里。

### 6.1 最小骨架

```python
class MyStrategy(bt.Strategy):
    params = dict(period=20)

    def __init__(self):
        pass

    def next(self):
        pass
```

### 6.2 策略参数 `params`

`backtrader` 的惯用法是把参数写在 `params` 中：

```python
class MyStrategy(bt.Strategy):
    params = dict(fast_period=10, slow_period=30)
```

在策略内部访问：

```python
self.p.fast_period
self.p.slow_period
```

也可以通过 `self.params` 访问，但更常见的是 `self.p`。

### 6.3 常见生命周期方法

```python
start(self)
prenext(self)
nextstart(self)
next(self)
stop(self)
notify_order(self, order)
notify_trade(self, trade)
```

### 6.4 周期说明

| API                   | 调用时机                            | 典型用途                       |
| --------------------- | ----------------------------------- | ------------------------------ |
| `start()`             | 回测刚开始时                        | 初始化全局状态、打印初始信息   |
| `prenext()`           | 指标未完全预热时，每根 Bar 仍会调用 | 处理预热阶段逻辑               |
| `nextstart()`         | 指标刚刚完成预热时                  | 从预热切换到正式逻辑           |
| `next()`              | 每根 Bar 调用一次                   | 写主要交易逻辑                 |
| `stop()`              | 回测结束时                          | 输出最终结果、做收尾           |
| `notify_order(order)` | 订单状态变化时                      | 处理订单提交、成交、拒绝、取消 |
| `notify_trade(trade)` | 交易状态变化时                      | 统计盈亏、输出交易结果         |

### 6.5 策略里最常用的属性

| 属性            | 说明                   |
| --------------- | ---------------------- |
| `self.datas`    | 所有数据源列表         |
| `self.data`     | `self.datas[0]` 的简写 |
| `self.position` | 当前默认数据源的持仓   |
| `self.broker`   | 当前策略关联的 Broker  |
| `self.p`        | 参数对象               |
| `len(self)`     | 当前已处理到第几根 Bar |

要注意，`self.order` 不是框架自动给你的固定属性，而是很多策略会自己维护的“当前挂单引用”。本项目就用了这个模式来避免重复下单。

### 6.6 交易相关方法

本地签名如下：

```python
buy(self, data=None, size=None, price=None, plimit=None, exectype=None,
    valid=None, tradeid=0, oco=None, trailamount=None, trailpercent=None,
    parent=None, transmit=True, **kwargs)

sell(self, data=None, size=None, price=None, plimit=None, exectype=None,
     valid=None, tradeid=0, oco=None, trailamount=None, trailpercent=None,
     parent=None, transmit=True, **kwargs)

close(self, data=None, size=None, **kwargs)
cancel(self, order)
getposition(self, data=None, broker=None)
```

### 6.7 这些方法怎么理解

| API                                   | 说明                         |
| ------------------------------------- | ---------------------------- |
| `buy()`                               | 发出买单                     |
| `sell()`                              | 发出卖单                     |
| `close()`                             | 让当前持仓回到 0，常用于平仓 |
| `cancel(order)`                       | 撤销未完成订单               |
| `getposition(data=None, broker=None)` | 查询某个数据源当前持仓       |

如果不传 `data`，默认使用 `self.data`。

### 6.8 本项目的策略实现重点

`strategy.py` 中的 `SmaCrossWithRiskStrategy` 演示了这些常见模式：

- `params` 定义策略参数
- `__init__` 中创建均线和 ATR 指标
- `next()` 中判断金叉、死叉、止损、止盈
- `notify_order()` 中读取真实成交价
- `notify_trade()` 中读取交易盈亏
- 用 `self.order` 避免未完成订单期间重复下单

## 7. Data Feed 与 Lines API

`backtrader` 的数据不是简单的 DataFrame，而是被包装成一组“线”对象。最常见的是：

- `open`
- `high`
- `low`
- `close`
- `volume`
- `openinterest`
- `datetime`

这些都可以像序列一样在策略中访问。

### 7.1 线的访问方式

```python
self.data.close[0]     # 当前 Bar 收盘价
self.data.close[-1]    # 上一根 Bar 收盘价
self.data.high[0]      # 当前最高价
self.data.datetime.date(0)  # 当前 Bar 日期
```

规则可以记成：

- `[0]` 表示当前值
- `[-1]` 表示上一根
- `[-2]` 表示前两根

`backtrader` 不是用 `for row in dataframe` 的方式写策略，而是让你在 `next()` 中直接读取这些 Lines。

### 7.2 `bt.feeds.PandasData`

本项目把 `pandas.DataFrame` 通过 `bt.feeds.PandasData` 喂给框架。

本地参数如下：

```python
('dataname', None)
('name', '')
('compression', 1)
('timeframe', 5)
('fromdate', None)
('todate', None)
('sessionstart', None)
('sessionend', None)
('filters', [])
('tz', None)
('tzinput', None)
('qcheck', 0.0)
('calendar', None)
('nocase', True)
('datetime', None)
('open', -1)
('high', -1)
('low', -1)
('close', -1)
('volume', -1)
('openinterest', -1)
```

### 7.3 这些参数最重要的部分

| 参数                                      | 含义                                          |
| ----------------------------------------- | --------------------------------------------- |
| `dataname`                                | DataFrame 本体                                |
| `datetime`                                | 时间列映射；`None` 时表示使用索引作为时间     |
| `open/high/low/close/volume/openinterest` | 各字段列映射                                  |
| `timeframe`                               | 数据周期，例如日线、分钟线                    |
| `compression`                             | 周期压缩倍数，例如 5 分钟线的 `compression=5` |

### 7.4 映射规则

在 `PandasData` 中，字段映射经常使用以下约定：

- `None`：没有该字段，或者时间来自索引
- `-1`：自动按列名匹配
- 整数：按列位置匹配
- 字符串：按列名匹配

因此，本项目返回的数据格式被整理成：

```text
index=datetime
columns=open, high, low, close, volume, openinterest
```

这样就可以直接：

```python
bt.feeds.PandasData(dataname=bt_df)
```

### 7.5 本项目的数据整理做了什么

`datasource.py` 中的 `fetch_bt_dataframe()` 会：

1. 校验 `ts_code`、日期和复权参数
2. 调用 `Tushare` 获取日线
3. 按需要获取复权因子
4. 执行前复权或后复权
5. 转换时间列为 `datetime`
6. 把 `vol` 转成 `volume`
7. 增加 `openinterest`
8. 把时间列设为索引

## 8. 指标 API

`backtrader` 的指标本质上也是 Lines。常用方式是在 `__init__()` 中创建指标，在 `next()` 中读取指标当前值。

### 8.1 基本写法

```python
self.fast_sma = bt.indicators.SimpleMovingAverage(self.data, period=10)
self.slow_sma = bt.indicators.SimpleMovingAverage(self.data, period=30)
self.atr = bt.indicators.AverageTrueRange(self.data, period=14)
self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)
```

### 8.2 使用方式

```python
if self.crossover > 0:
    self.buy()

if self.data.close[0] < self.fast_sma[0]:
    self.close()
```

要点有两个：

1. 指标对象本身就是“可随时间推进的序列”。
2. 在 `next()` 中取值时，通常还是用 `[0]`、`[-1]` 这种方式。

### 8.3 常见内置指标

| 指标类                                   | 作用           |
| ---------------------------------------- | -------------- |
| `bt.indicators.SimpleMovingAverage`      | 简单移动平均线 |
| `bt.indicators.ExponentialMovingAverage` | 指数移动平均线 |
| `bt.indicators.AverageTrueRange`         | ATR 波动率指标 |
| `bt.indicators.RSI`                      | 相对强弱指标   |
| `bt.indicators.MACD`                     | MACD           |
| `bt.indicators.BollingerBands`           | 布林带         |
| `bt.indicators.CrossOver`                | 两条线交叉检测 |

### 8.4 本项目如何用指标

本项目用到了：

- `SimpleMovingAverage`
- `AverageTrueRange`
- `CrossOver`

用途分别是：

- 均线判断趋势
- ATR 计算止损和止盈距离
- `CrossOver` 直接判断金叉死叉

## 9. Broker API

Broker 负责账户资金、持仓估值、交易成本和成交处理。你既可以通过 `cerebro.broker` 在外部配置，也可以在策略内部通过 `self.broker` 访问同一个对象。

### 9.1 本地常用方法签名

```python
setcash(self, cash)
getcash(self)
getvalue(self, datas=None, mkt=False, lever=False)
setcommission(self, commission=0.0, margin=None, mult=1.0, commtype=None,
              percabs=True, stocklike=False, interest=0.0,
              interest_long=False, leverage=1.0, automargin=False, name=None)
set_slippage_perc(self, perc, slip_open=True, slip_limit=True,
                  slip_match=True, slip_out=False)
```

### 9.2 常用调用方式

```python
cerebro.broker.setcash(100000)
cerebro.broker.setcommission(commission=0.001)
cerebro.broker.set_slippage_perc(perc=0.0005)
```

### 9.3 方法说明

| API                 | 说明           |
| ------------------- | -------------- |
| `setcash`           | 设置初始资金   |
| `getcash`           | 获取当前现金   |
| `getvalue`          | 获取当前总资产 |
| `setcommission`     | 设置手续费模型 |
| `set_slippage_perc` | 设置按比例滑点 |

### 9.4 本项目如何使用 Broker

本项目只做了最常见的三件事：

- 设置初始资金
- 设置百分比手续费
- 设置百分比滑点

这已经足够说明 Broker API 的核心入口。

## 10. Order API

订单是策略和 Broker 之间的桥梁。`buy()`、`sell()`、`close()` 只是发出订单，真正的成交状态要通过 `notify_order()` 追踪。

### 10.1 常见下单方式

```python
self.buy(size=100)
self.sell(size=100)
self.close()
```

### 10.2 订单执行类型

本地 `bt.Order.ExecTypes` 为：

```text
Market
Close
Limit
Stop
StopLimit
StopTrail
StopTrailLimit
Historical
```

常见用法：

```python
self.buy(exectype=bt.Order.Market)
self.buy(price=10.5, exectype=bt.Order.Limit)
self.sell(price=9.8, exectype=bt.Order.Stop)
```

### 10.3 订单状态

本地 `bt.Order.Status` 为：

```text
Created
Submitted
Accepted
Partial
Completed
Canceled
Expired
Margin
Rejected
```

### 10.4 `notify_order(order)` 里通常看什么

最常见的是：

```python
order.status
order.isbuy()
order.issell()
order.getstatusname()
order.executed.price
order.executed.size
order.executed.value
order.executed.comm
```

示例：

```python
def notify_order(self, order):
    if order.status in [order.Submitted, order.Accepted]:
        return

    if order.status == order.Completed:
        print(order.executed.price, order.executed.size)
```

### 10.5 本项目如何使用订单 API

本项目在 `notify_order()` 中做了这些事：

- 过滤 `Submitted` 和 `Accepted`
- 判断是否成交
- 买单成交后记录入场价
- 根据 ATR 计算止损价和止盈价
- 卖单成交后清理持仓状态
- 对 `Canceled`、`Margin`、`Rejected` 打日志

## 11. Trade API

`Trade` 代表一笔完整交易的状态聚合，通常在 `notify_trade(self, trade)` 中使用。

### 11.1 常见属性

本地可见的常用字段包括：

```text
size
price
value
commission
pnl
pnlcomm
isclosed
isopen
justopened
baropen
barclose
barlen
```

### 11.2 典型写法

```python
def notify_trade(self, trade):
    if not trade.isclosed:
        return
    print(trade.pnl, trade.pnlcomm)
```

### 11.3 `Trade` 和 `Order` 的区别

| 对象    | 关注点                     |
| ------- | -------------------------- |
| `Order` | 单次下单、改单、成交状态   |
| `Trade` | 一笔完整开平仓后的盈亏聚合 |

简单理解：

- `Order` 更偏执行层
- `Trade` 更偏结果层

## 12. Observer API

Observer 主要用于观察图上的内容和账户状态变化，它更偏“展示”和“过程观察”，不负责策略评分。

### 12.1 注册方式

```python
cerebro.addobserver(bt.observers.Broker)
cerebro.addobserver(bt.observers.BuySell)
cerebro.addobserver(bt.observers.Value)
cerebro.addobserver(bt.observers.DrawDown)
```

### 12.2 本项目使用的观察器

| Observer   | 作用               |
| ---------- | ------------------ |
| `Broker`   | 观察现金与资产变化 |
| `BuySell`  | 在图上标注买卖点   |
| `Value`    | 观察净值变化       |
| `DrawDown` | 观察回撤曲线       |

### 12.3 `Observer` 和 `Analyzer` 的区别

| 类型       | 主要用途                   |
| ---------- | -------------------------- |
| `Observer` | 观察过程、配合绘图         |
| `Analyzer` | 输出统计结果、便于程序读取 |

## 13. Analyzer API

Analyzer 用来做回测结果统计。它和 Observer 不同，重点是返回结构化结果而不是画图。

### 13.1 注册方式

```python
cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", annualize=True)
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
```

### 13.2 读取方式

```python
results = cerebro.run()
strategy = results[0]
analysis = strategy.analyzers.returns.get_analysis()
```

关键点：

- `_name` 决定后续访问名
- 通过 `strategy.analyzers.<name>.get_analysis()` 读取结果

### 13.3 本项目使用的分析器

| Analyzer        | 说明        | 常见 key                                       |
| --------------- | ----------- | ---------------------------------------------- |
| `Returns`       | 收益率分析  | `rtot`, `ravg`, `rnorm`, `rnorm100`            |
| `DrawDown`      | 回撤分析    | `drawdown`, `moneydown`, `max.drawdown`        |
| `SharpeRatio`   | Sharpe 比率 | `sharperatio`                                  |
| `TradeAnalyzer` | 交易统计    | `total`, `won`, `lost`, `pnl`, `streak`, `len` |

### 13.4 本地实际 `get_analysis()` 结果特征

本项目当前环境里，这几个分析器的结果结构大致如下：

```python
Returns:
{'rtot': ..., 'ravg': ..., 'rnorm': ..., 'rnorm100': ...}

DrawDown:
{'len': ..., 'drawdown': ..., 'moneydown': ...,
 'max': {'len': ..., 'drawdown': ..., 'moneydown': ...}}

SharpeRatio:
{'sharperatio': ...}

TradeAnalyzer:
{'total': {...}, 'streak': {...}, 'pnl': {...}, 'won': {...},
 'lost': {...}, 'long': {...}, 'short': {...}, 'len': {...}}
```

要注意，`SharpeRatio` 在样本太短或波动特征不足时可能返回 `None`，本项目的 `main.py` 已经做了兼容处理。

## 14. 多数据、多周期 API

虽然本项目当前只加载了一只股票的一份日线数据，但 `backtrader` 在这方面的 API 很重要。

### 14.1 多数据

```python
cerebro.adddata(data0, name="000001.SZ")
cerebro.adddata(data1, name="600519.SH")
```

在策略里访问：

```python
self.datas[0]
self.datas[1]
self.datas[0].close[0]
self.datas[1].close[0]
```

### 14.2 重采样

```python
cerebro.resampledata(data, timeframe=bt.TimeFrame.Weeks, compression=1)
```

常见含义：

- `timeframe=bt.TimeFrame.Minutes`
- `timeframe=bt.TimeFrame.Days`
- `timeframe=bt.TimeFrame.Weeks`
- `timeframe=bt.TimeFrame.Months`

### 14.3 重放

```python
cerebro.replaydata(data, timeframe=bt.TimeFrame.Days, compression=1)
```

`replaydata()` 和 `resampledata()` 都和多周期有关，但语义不同：

- `resampledata()` 更像“直接压缩成新周期”
- `replaydata()` 更像“让高周期 Bar 在回测中逐步形成”

## 15. 本项目如何映射到这些 API

### 15.1 `main.py`

负责：

- 参数解析
- 创建 `Cerebro`
- 加载 `PandasData`
- 配置 Broker
- 注册 Observer
- 注册 Analyzer
- 执行 `run()`
- 输出摘要

### 15.2 `strategy.py`

负责：

- 定义 `Strategy`
- 配置 `params`
- 创建均线、ATR、CrossOver 指标
- 处理 `next()`
- 处理 `notify_order()`
- 处理 `notify_trade()`

### 15.3 `datasource.py`

负责：

- 拉取 `Tushare` 日线
- 复权
- 清洗缺失值
- 整理成 `PandasData` 可直接使用的 DataFrame

## 16. 运行参数

| 参数                | 说明                             | 默认值      |
| ------------------- | -------------------------------- | ----------- |
| `--ts-code`         | Tushare 股票代码                 | `000001.SZ` |
| `--start-date`      | 开始日期，格式 `YYYYMMDD`        | `20200101`  |
| `--end-date`        | 结束日期，格式 `YYYYMMDD`        | `20250101`  |
| `--adjust`          | 复权方式：`none` / `qfq` / `hfq` | `hfq`       |
| `--cash`            | 初始资金                         | `100000`    |
| `--commission`      | 手续费比例                       | `0.001`     |
| `--slippage`        | 滑点比例                         | `0.0`       |
| `--fast-period`     | 短周期均线窗口                   | `10`        |
| `--slow-period`     | 长周期均线窗口                   | `30`        |
| `--atr-period`      | ATR 窗口                         | `14`        |
| `--position-pct`    | 每次进场资金占比                 | `0.95`      |
| `--stop-loss-atr`   | 止损 ATR 倍数                    | `2.0`       |
| `--take-profit-atr` | 止盈 ATR 倍数                    | `4.0`       |
| `--token`           | 显式传入 Tushare Token           | `None`      |
| `--plot`            | 绘图                             | 关闭        |
| `--no-log`          | 关闭策略日志                     | 关闭        |

## 17. 常见注意事项

### 17.1 `buy()` 不等于立即成交

`buy()`、`sell()` 返回的是订单对象，真实成交要看 `notify_order()`。

### 17.2 `next()` 里读到的是当前 Bar，默认市场单通常在下一根 Bar 执行

所以“信号出现日期”和“实际成交日期”不一定是同一天。

### 17.3 `PandasData` 的时间列和列名最容易出问题

如果用自己的数据源，请优先确认：

- 时间是否真的是 `datetime`
- 时间是否在索引里
- `open/high/low/close/volume/openinterest` 是否能正确映射
