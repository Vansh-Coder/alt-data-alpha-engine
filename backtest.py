import os
import numpy as np
import pandas as pd
import backtrader as bt
import yfinance as yf
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────
DATA_DIR        = 'data'
SIGNALS_FILE    = os.path.join(DATA_DIR, 'signals_5d.csv')  # default for CLI runs

START_CASH      = 100_000
COMMISSION      = 0.001
STOP_LOSS_PCT   = 0.02    # default stop-loss, overridable
TAKE_PROFIT_PCT = 0.02    # default take-profit, overridable
TIME_EXIT_DAYS  = 5       # fallback hard exit

# ─── Data helper ───────────────────────────────────────────────────────────────
def fetch_price_data(ticker, start, end):
    try:
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch history for {ticker}: {e}")
    df = hist[['Open','High','Low','Close','Volume']].rename(columns=str.lower)
    df.dropna(inplace=True)
    return df

# ─── Strategy definition ───────────────────────────────────────────────────────
class SignalStrategy(bt.Strategy):
    params = (('signal_df', None), ('printlog', False),)

    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def __init__(self):
        # Copy and normalize the incoming DataFrame
        sig = self.params.signal_df.copy()
        sig['timestamp'] = pd.to_datetime(sig['timestamp'], utc=True).dt.date
        sig = sig.drop_duplicates(['timestamp', 'ticker'])

        # Ensure there is always a 'conv' column (default 0.0)
        if 'conv' not in sig.columns:
            sig['conv'] = 0.0

        # Build lookup maps
        self.signal_map = sig.set_index(['timestamp', 'ticker'])['signal'].to_dict()
        self.conv_map   = sig.set_index(['timestamp', 'ticker'])['conv'].to_dict()

        # Tracking structures
        self.entry_price = {}
        self.entry_date  = {}
        self.trail_stop  = {}

    def next(self):
        for data in self.datas:
            dt     = data.datetime.date(0)
            ticker = data._name
            price  = data.close[0]

            # Skip invalid price bars
            if not np.isfinite(price) or price <= 0:
                continue

            signal = self.signal_map.get((dt, ticker), 'Neutral')
            pos    = self.getposition(data).size

            ep = self.entry_price.get(ticker)
            ed = self.entry_date.get(ticker)

            # ─── Manage open positions ─────────────────────────────
            if pos and ep is not None:
                if pos > 0:
                    # Update trailing stop
                    prev_stop = self.trail_stop.get(ticker, ep * (1 - STOP_LOSS_PCT))
                    new_stop  = data.high[0] * (1 - STOP_LOSS_PCT)
                    self.trail_stop[ticker] = max(prev_stop, new_stop)

                    # Trailing stop exit
                    if price < self.trail_stop[ticker]:
                        self.log(f'TRAIL STOP EXIT {ticker} @ {price:.2f}', dt)
                        self.close(data=data)
                        self.entry_price.pop(ticker, None)
                        self.entry_date.pop(ticker, None)
                        self.trail_stop.pop(ticker, None)
                        continue

                    # Static take-profit exit
                    if price / ep - 1 >= TAKE_PROFIT_PCT:
                        self.log(f'TP EXIT {ticker} @ {price:.2f}', dt)
                        self.close(data=data)
                        self.entry_price.pop(ticker, None)
                        self.entry_date.pop(ticker, None)
                        self.trail_stop.pop(ticker, None)
                        continue
                else:
                    # Short SL/TP exit
                    pnl_pct = ep / price - 1
                    if pnl_pct <= -STOP_LOSS_PCT or pnl_pct >= TAKE_PROFIT_PCT:
                        self.log(f'SHORT EXIT {ticker} @ {price:.2f} (pnl={pnl_pct:.3f})', dt)
                        self.close(data=data)
                        self.entry_price.pop(ticker, None)
                        self.entry_date.pop(ticker, None)
                        continue

                # Fallback time-based exit
                if (dt - ed).days >= TIME_EXIT_DAYS:
                    self.log(f'TIME EXIT {ticker} @ {price:.2f} (days={(dt-ed).days})', dt)
                    self.close(data=data)
                    self.entry_price.pop(ticker, None)
                    self.entry_date.pop(ticker, None)
                    self.trail_stop.pop(ticker, None)
                    continue

            # ─── Entry logic with conviction sizing ───────────────────
            if pos == 0 and signal in ('Long', 'Short'):
                raw_conv = self.conv_map.get((dt, ticker), 0.0)
                conv     = float(raw_conv) if np.isfinite(raw_conv) else 0.0
                frac     = min(conv, 1.0)
                cash     = self.broker.getcash()
                alloc    = cash * frac
                size     = max(1, int(alloc / price))
                self.log(f'ENTER {signal} {ticker} @ {price:.2f} size={size}', dt)

                if signal == 'Long':
                    self.buy(data=data, size=size)
                    self.trail_stop[ticker] = price * (1 - STOP_LOSS_PCT)
                else:
                    self.sell(data=data, size=size)

                self.entry_price[ticker] = price
                self.entry_date[ticker]  = dt

            # ─── Exit on reverse/neutral signal ──────────────────────
            elif pos != 0:
                if (pos > 0 and signal in ('Short','Neutral')) or (pos < 0 and signal in ('Long','Neutral')):
                    self.log(f'SIGNAL EXIT {ticker} @ {price:.2f} (sig={signal})', dt)
                    self.close(data=data)
                    self.entry_price.pop(ticker, None)
                    self.entry_date.pop(ticker, None)
                    self.trail_stop.pop(ticker, None)

    def stop(self):
        pnl = self.broker.getvalue() - START_CASH
        print(f'Ending Value: {self.broker.getvalue():.2f}, PnL: {pnl:.2f}')


# ─── Programmatic backtest runner ──────────────────────────────────────────────

def run_backtest(signals_df, stop_loss_pct, take_profit_pct, price_cache):
    global STOP_LOSS_PCT, TAKE_PROFIT_PCT
    prev_sl, prev_tp = STOP_LOSS_PCT, TAKE_PROFIT_PCT
    STOP_LOSS_PCT, TAKE_PROFIT_PCT = stop_loss_pct, take_profit_pct

    df = signals_df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    start = df['timestamp'].min().date().isoformat()
    end   = (df['timestamp'].max().date() + timedelta(days=1)).isoformat()

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(START_CASH)
    cerebro.broker.setcommission(COMMISSION)
    cerebro.addobserver(bt.observers.Broker)

    for ticker in df['ticker'].unique():
        hist = price_cache.get(ticker)
        if hist is None or hist.empty:
            continue
        feed = bt.feeds.PandasData(dataname=hist)
        feed.plotinfo.plot = False
        cerebro.adddata(feed, name=ticker)

    cerebro.addstrategy(SignalStrategy, signal_df=df, printlog=False)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio,   _name='sharpe', timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown,      _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer,_name='trades')

    results = cerebro.run()
    STOP_LOSS_PCT, TAKE_PROFIT_PCT = prev_sl, prev_tp

    if not results:
        return {'sharpe': None, 'cagr': None, 'max_dd': None, 'trades': 0, 'win_rate': None}

    strat    = results[0]
    end_val  = cerebro.broker.getvalue()

    sr       = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
    sharpe   = float(sr) if sr is not None else None
    dd       = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
    ti       = strat.analyzers.trades.get_analysis().get('total', {})
    closed   = ti.get('closed', 0)
    won      = strat.analyzers.trades.get_analysis().get('won', {}).get('total', 0)
    win_rate = (won / closed) if closed else None
    days     = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days or 1
    cagr     = (end_val / START_CASH)**(252/days) - 1 if days else None

    return {
        'sharpe': sharpe,
        'cagr':   cagr,
        'max_dd': dd,
        'trades': closed,
        'win_rate': win_rate
    }


# ─── CLI backtest ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    signals = pd.read_csv(SIGNALS_FILE)
    signals['timestamp'] = (
        pd.to_datetime(signals['timestamp'], utc=True)
          .dt.normalize()
          + timedelta(days=1)
    )

    start = signals['timestamp'].min().date().isoformat()
    end   = (signals['timestamp'].max().date() + timedelta(days=1)).isoformat()

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(START_CASH)
    cerebro.broker.setcommission(COMMISSION)
    cerebro.addobserver(bt.observers.Broker)

    for ticker in signals['ticker'].unique():
        df      = fetch_price_data(ticker, start, end)
        feed    = bt.feeds.PandasData(dataname=df)
        feed.plotinfo.plot = False
        cerebro.adddata(feed, name=ticker)

    cerebro.addstrategy(SignalStrategy, signal_df=signals, printlog=False)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio,   _name='sharpe', timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown,      _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer,_name='trades')

    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():,.2f}')
    results = cerebro.run()
    strat    = results[0]
    end_val  = cerebro.broker.getvalue()

    sr       = strat.analyzers.sharpe.get_analysis().get('sharperatio', float('nan'))
    dd       = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
    ti       = strat.analyzers.trades.get_analysis().get('total', {})
    closed   = ti.get('closed', 0)
    won      = strat.analyzers.trades.get_analysis().get('won', {}).get('total', 0)
    winr     = (won / closed) if closed else float('nan')
    days     = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days or 1
    cagr     = (end_val / START_CASH)**(252/days) - 1

    print(f'Final Portfolio Value: {end_val:,.2f}')
    print(f'CAGR (approx):           {cagr:.2%}')
    print(f'Sharpe Ratio:            {sr:.2f}')
    print(f'Max Drawdown:            {dd:.2f}%')
    print(f'Total Trades:            {closed}')
    print(f'Win Rate:                {winr:.2%}')

    cerebro.plot(numfigs=1)