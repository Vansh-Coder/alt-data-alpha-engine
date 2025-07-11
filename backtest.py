import os
import pandas as pd
import backtrader as bt
import yfinance as yf
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────
DATA_DIR         = 'data'
SIGNALS_FILE     = os.path.join(DATA_DIR, 'signals_5d.csv')  # default for manual runs

START_CASH       = 100_000
COMMISSION        = 0.001
STOP_LOSS_PCT     = 0.02    # default stop-loss, overridable in run_backtest
TAKE_PROFIT_PCT   = 0.02    # default take-profit, overridable in run_backtest
TIME_EXIT_DAYS    = 5       # hard exit, not used if trailing stop implemented

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
    params = (
        ('signal_df', None),
        ('printlog', False),
    )

    def log(self, txt, dt=None):
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def __init__(self):
        sig = self.params.signal_df.copy()
        sig['timestamp'] = pd.to_datetime(sig['timestamp'], utc=True).dt.date
        sig = sig.drop_duplicates(subset=['timestamp','ticker'], keep='last')
        self.signal_map = sig.set_index(['timestamp','ticker'])['signal'].to_dict()
        self.entry_price = {}
        self.entry_date  = {}

    def next(self):
        for data in self.datas:
            dt     = data.datetime.date(0)
            ticker = data._name
            signal = self.signal_map.get((dt, ticker), 'Neutral')
            pos    = self.getposition(data).size
            price  = data.close[0]

            ep = self.entry_price.get(ticker)
            ed = self.entry_date.get(ticker)
            if pos and ep is not None:
                pnl_pct = (price/ep - 1) if pos > 0 else (ep/price - 1)
                if pnl_pct <= -STOP_LOSS_PCT or pnl_pct >= TAKE_PROFIT_PCT:
                    self.log(f'RISK EXIT {ticker} @ {price:.2f} (pnl_pct={pnl_pct:.3f})', dt)
                    self.close(data=data)
                    del self.entry_price[ticker]
                    del self.entry_date[ticker]
                    continue
                if (dt - ed).days >= TIME_EXIT_DAYS:
                    self.log(f'TIME EXIT {ticker} @ {price:.2f} (days={(dt-ed).days})', dt)
                    self.close(data=data)
                    del self.entry_price[ticker]
                    del self.entry_date[ticker]
                    continue

            if pos == 0 and signal in ('Long','Short'):
                self.log(f'ENTER {signal} {ticker} @ {price:.2f}', dt)
                if signal == 'Long': self.buy(data=data)
                else:                 self.sell(data=data)
                self.entry_price[ticker] = price
                self.entry_date[ticker]  = dt

            elif pos != 0:
                if (pos>0 and signal in ('Short','Neutral')) or (pos<0 and signal in ('Long','Neutral')):
                    self.log(f'EXIT  {ticker} @ {price:.2f} (sig={signal})', dt)
                    self.close(data=data)
                    del self.entry_price[ticker]
                    del self.entry_date[ticker]

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
    cerebro.broker.setcommission(commission=COMMISSION)
    cerebro.addobserver(bt.observers.Broker)

    for ticker in df['ticker'].unique():
        hist = price_cache.get(ticker)
        if hist is None or hist.empty: continue
        feed = bt.feeds.PandasData(dataname=hist)
        feed.plotinfo.plot = False; cerebro.adddata(feed, name=ticker)

    cerebro.addstrategy(SignalStrategy, signal_df=df, printlog=False)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio,   _name='sharpe',   timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown,      _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    results = cerebro.run()
    STOP_LOSS_PCT, TAKE_PROFIT_PCT = prev_sl, prev_tp

    if not results: return {'sharpe':None,'cagr':None,'max_dd':None,'trades':0,'win_rate':None}
    strat   = results[0]; end_val = cerebro.broker.getvalue()

    sharpe_raw = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
    sharpe     = float(sharpe_raw) if sharpe_raw is not None else None
    dd_info    = strat.analyzers.drawdown.get_analysis().get('max', {})
    max_dd     = dd_info.get('drawdown', 0.0)
    tinfo      = strat.analyzers.trades.get_analysis().get('total', {})
    closed     = tinfo.get('closed', 0)
    won        = strat.analyzers.trades.get_analysis().get('won', {}).get('total',0)
    win_rate   = (won/closed) if closed else None
    days       = (datetime.fromisoformat(end)-datetime.fromisoformat(start)).days or 1
    cagr       = (end_val/START_CASH)**(252/days)-1 if days else None

    return {'sharpe':sharpe, 'cagr':cagr, 'max_dd':max_dd, 'trades':closed, 'win_rate':win_rate}

# ─── CLI backtest ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    signals = pd.read_csv(SIGNALS_FILE)
    signals['timestamp'] = (
        pd.to_datetime(signals['timestamp'], utc=True).dt.normalize() + timedelta(days=1)
    )
    start = signals['timestamp'].min().date().isoformat()
    end   = (signals['timestamp'].max().date()+timedelta(days=1)).isoformat()

    cerebro = bt.Cerebro(); cerebro.broker.setcash(START_CASH); cerebro.broker.setcommission(COMMISSION)
    for ticker in signals['ticker'].unique():
        df = fetch_price_data(ticker, start, end)
        feed = bt.feeds.PandasData(dataname=df); feed.plotinfo.plot=False; cerebro.adddata(feed,name=ticker)

    cerebro.addstrategy(SignalStrategy, signal_df=signals, printlog=False)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio,_name='sharpe',timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown,_name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer,_name='trades')
    cerebro.addobserver(bt.observers.Broker)

    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():,.2f}")
    results = cerebro.run(); strat=results[0]; end_val=cerebro.broker.getvalue()

    # guard None metrics
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
    sharpe = sharpe if sharpe is not None else float('nan')
    max_dd = strat.analyzers.drawdown.get_analysis().get('max',{}).get('drawdown',0.0)
    trades = strat.analyzers.trades.get_analysis().get('total',{}).get('closed',0)
    won    = strat.analyzers.trades.get_analysis().get('won',{}).get('total',0)
    winrate= (won/trades) if trades else float('nan')
    days   = (datetime.fromisoformat(end)-datetime.fromisoformat(start)).days or 1
    cagr   = (end_val/START_CASH)**(252/days)-1

    print(f"Final Portfolio Value: {end_val:,.2f}")
    print(f"CAGR (approx):           {cagr:.2%}")
    print(f"Sharpe Ratio:            {sharpe:.2f}")
    print(f"Max Drawdown:            {max_dd:.2f}%")
    print(f"Total Trades:            {trades}")
    print(f"Win Rate:                {winrate:.2%}")

    cerebro.plot(numfigs=1)