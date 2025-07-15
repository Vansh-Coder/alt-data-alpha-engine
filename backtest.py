import numpy as np
import pandas as pd
import backtrader as bt
from datetime import timedelta
from functools import lru_cache
import yfinance as yf

# ─── Configuration ─────────────────────────────────────────────────────────────
START_CASH     = 100_000
COMMISSION     = 0.001
TIME_EXIT_DAYS = 5

# global price cache
price_cache = {}

@lru_cache(maxsize=None)
def fetch_price_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Download OHLCV history for `ticker` between `start` and `end`.
    """
    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    df = hist[['Open','High','Low','Close','Volume']].rename(columns=str.lower)
    df.dropna(inplace=True)
    return df

class SignalStrategy(bt.Strategy):
    params = (
        ('signal_df',   None),
        ('stop_loss',   0.02),
        ('take_profit', 0.04),
        ('printlog',    False),
    )

    def __init__(self):
        sig = self.params.signal_df.copy()
        sig['timestamp'] = pd.to_datetime(sig['timestamp'], utc=True).dt.date
        if 'conv' not in sig:
            sig['conv'] = 1.0
        sig = sig.drop_duplicates(['timestamp','ticker'])

        self.signal_map = sig.set_index(['timestamp','ticker'])['signal'].to_dict()
        self.conv_map   = sig.set_index(['timestamp','ticker'])['conv'].to_dict()
        self.entry_price = {}
        self.entry_date  = {}
        self.trail_stop  = {}

    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def _clear_position(self, ticker):
        self.entry_price.pop(ticker, None)
        self.entry_date.pop(ticker, None)
        self.trail_stop.pop(ticker, None)

    def next(self):
        sl = self.params.stop_loss
        tp = self.params.take_profit

        for data in self.datas:
            dt     = data.datetime.date(0)
            ticker = data._name
            price  = data.close[0]
            if not np.isfinite(price) or price <= 0:
                continue

            signal = self.signal_map.get((dt, ticker), 'Neutral')
            pos    = self.getposition(data).size
            ep     = self.entry_price.get(ticker)
            ed     = self.entry_date.get(ticker)

            # ─── Manage open positions ─────────────────────────────
            if pos and ep is not None:
                # ── LONG position management ─────────────────────────
                if pos > 0:
                    prev_stop = self.trail_stop.get(ticker, ep * (1 - sl))
                    new_stop  = data.high[0] * (1 - sl)
                    self.trail_stop[ticker] = max(prev_stop, new_stop)

                    # trailing stop exit
                    if price < self.trail_stop[ticker]:
                        self.log(f'TRAIL STOP EXIT {ticker} @ {price:.2f}', dt)
                        self.close(data=data)
                        self._clear_position(ticker)
                        continue

                    # take-profit exit
                    if price / ep - 1 >= tp:
                        self.log(f'TP EXIT {ticker} @ {price:.2f}', dt)
                        self.close(data=data)
                        self._clear_position(ticker)
                        continue

                # ── SHORT position management ────────────────────────
                else:
                    pnl_pct = ep / price - 1
                    if pnl_pct <= -sl or pnl_pct >= tp:
                        self.log(f'SHORT EXIT {ticker} @ {price:.2f} (pnl={pnl_pct:.3f})', dt)
                        self.close(data=data)
                        self._clear_position(ticker)
                        continue

                # ── Hard time-based exit ─────────────────────────────
                if (dt - ed).days >= TIME_EXIT_DAYS:
                    self.log(f'TIME EXIT {ticker} @ {price:.2f}', dt)
                    self.close(data=data)
                    self._clear_position(ticker)
                    continue

            # ─── Entry logic ────────────────────────────────────────
            if pos == 0 and signal in ('Long', 'Short'):
                conv = float(self.conv_map.get((dt, ticker), 0.0))
                frac = min(conv, 1.0)
                alloc = self.broker.get_cash() * frac
                size  = max(1, int(alloc / price))

                self.log(f'ENTER {signal} {ticker} @ {price:.2f} size={size}', dt)
                if signal == 'Long':
                    self.buy(data=data, size=size)
                    self.trail_stop[ticker] = price * (1 - sl)
                else:
                    self.sell(data=data, size=size)

                self.entry_price[ticker] = price
                self.entry_date[ticker]  = dt

            # ─── Exit on reverse/neutral signal ────────────────────
            elif pos != 0:
                reverse = (pos > 0 and signal in ('Short', 'Neutral')) \
                       or (pos < 0 and signal in ('Long',  'Neutral'))
                if reverse:
                    self.log(f'SIGNAL EXIT {ticker} @ {price:.2f}', dt)
                    self.close(data=data)
                    self._clear_position(ticker)

    def stop(self):
        # No CLI output here; metrics are extracted separately
        pass


def run_backtest(
    signals_df: pd.DataFrame,
    stop_loss: float = 0.02,
    take_profit: float = 0.04,
    external_price_cache: dict = None,
) -> tuple:
    """
    Run a Cerebro backtest and return (cerebro, strat, start_date, end_date).
    """
    pc = external_price_cache or price_cache
    df = signals_df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    start = df['timestamp'].min().date()
    end   = df['timestamp'].max().date() + timedelta(days=1)

    if pc is price_cache and not pc:
        for t in df['ticker'].unique():
            pc[t] = fetch_price_data(t, start.isoformat(), end.isoformat())

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(START_CASH)
    cerebro.broker.setcommission(COMMISSION)

    for ticker, hist in pc.items():
        if hist is None or hist.empty:
            continue
        feed = bt.feeds.PandasData(dataname=hist)
        feed.plotinfo.plot = False
        cerebro.adddata(feed, name=ticker)

    cerebro.addstrategy(
        SignalStrategy,
        signal_df=signals_df,
        stop_loss=stop_loss,
        take_profit=take_profit
    )
    cerebro.addanalyzer(bt.analyzers.SharpeRatio,   _name='sharpe',   timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown,      _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    results = cerebro.run()
    strat   = results[0] if results else None
    return cerebro, strat, start, end