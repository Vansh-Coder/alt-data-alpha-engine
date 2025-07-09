# import os
# import pandas as pd
# import backtrader as bt
# import yfinance as yf
# from datetime import datetime

# # Paths
# DATA_DIR = 'data'
# SIGNALS_FILE = os.path.join(DATA_DIR, 'signals_1d.csv')  # 1-day signals file

# # 1. Fetch and prepare price data

# def fetch_price_data(ticker, start, end):
#     """
#     Download OHLCV data for `ticker` between `start` and `end` using yfinance Ticker.history,
#     return DataFrame indexed by date with lowercase columns ['open','high','low','close','volume'].
#     """
#     # Use history() to get clean single-index columns
#     try:
#         hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
#     except Exception as e:
#         raise RuntimeError(f"Failed to fetch history for {ticker}: {e}")

#     # Ensure required columns exist
#     for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
#         if col not in hist.columns:
#             raise ValueError(f"Missing '{col}' in price data for {ticker}")

#     # Select and lowercase
#     df = hist[['Open', 'High', 'Low', 'Close', 'Volume']].rename(columns=str.lower)
#     # Drop any rows with NaNs
#     df.dropna(inplace=True)
#     return df
# [['open', 'high', 'low', 'close', 'volume']]

# # 2. Define strategy based on signals
# class SignalStrategy(bt.Strategy):
#     params = (
#         ('signal_df', None),
#         ('printlog', False),
#     )

#     def log(self, txt, dt=None):
#         if self.params.printlog:
#             dt = dt or self.datas[0].datetime.date(0)
#             print(f'{dt.isoformat()} {txt}')

#     def __init__(self):
#         # Prepare a mapping of (date, ticker) -> signal
#         sig = self.params.signal_df.copy()
#         sig['timestamp'] = pd.to_datetime(sig['timestamp'], utc=True).dt.date
#         sig = sig.drop_duplicates(subset=['timestamp', 'ticker'], keep='last')
#         self.signal_map = sig.set_index(['timestamp', 'ticker'])['signal'].sort_index()
#         self.dataclose = self.datas[0].close

#     def next(self):
#         dt = self.datas[0].datetime.date(0)
#         ticker = self.datas[0]._name
#         key = (dt, ticker)
#         if key in self.signal_map:
#             signal = self.signal_map.loc[key]
#             pos = self.getposition(self.datas[0]).size
#             price = self.dataclose[0]
#             if signal == 'Long' and pos == 0:
#                 self.log(f'BUY CREATE {ticker}, {price:.2f}')
#                 self.buy()
#             elif signal == 'Short' and pos == 0:
#                 self.log(f'SELL SHORT CREATE {ticker}, {price:.2f}')
#                 self.sell()
#             elif signal == 'Neutral' and pos != 0:
#                 self.log(f'CLOSE POSITION {ticker}, {price:.2f}')
#                 self.close()

#     def stop(self):
#         pnl = round(self.broker.getvalue() - self.broker.startingcash, 2)
#         print(f'Ending Value: {self.broker.getvalue():.2f}, PnL: {pnl}')

# # 3. Run backtest
# if __name__ == '__main__':
#     # Load signals
#     signals = pd.read_csv(SIGNALS_FILE)
#     signals['timestamp'] = pd.to_datetime(signals['timestamp'], utc=True)

#     # Determine date range (inclusive)
#     start = signals['timestamp'].min().date().isoformat()
#     end   = (signals['timestamp'].max().date() + pd.Timedelta(days=1)).isoformat()

#     cerebro = bt.Cerebro()
#     cerebro.broker.setcash(100000.0)
#     cerebro.broker.setcommission(commission=0.001)

#     # Add data feeds for each ticker
#     for ticker in signals['ticker'].unique():
#         price_df = fetch_price_data(ticker, start, end)
#         data_feed = bt.feeds.PandasData(dataname=price_df)
#         cerebro.adddata(data_feed, name=ticker)

#     cerebro.addstrategy(SignalStrategy, signal_df=signals, printlog=False)

#     # add analyzers
#     cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days)
#     cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
#     cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

#     # record starting value
#     start_val = cerebro.broker.getvalue()
#     print(f"Starting Portfolio Value: {start_val:,.2f}")

#     # run once
#     results = cerebro.run()
#     strat = results[0]
#     end_val = cerebro.broker.getvalue()

#     # pull analyzer stats safely
#     sharpe_ratio = strat.analyzers.sharpe.get_analysis().get("sharperatio", float('nan'))
#     dd_stats = strat.analyzers.drawdown.get_analysis()
#     max_dd = dd_stats.get("max", {}).get("drawdown", 0.0)

#     trade_stats  = strat.analyzers.trades.get_analysis()
#     total_closed = trade_stats.get("total", {}).get("closed", 0)
#     won_trades = trade_stats.get("won", {}).get("total",  0)
#     win_rate = (won_trades / total_closed) if total_closed else float('nan')

#     # approximate CAGR
#     days = (pd.to_datetime(end) - pd.to_datetime(start)).days or 1
#     cagr = (end_val / start_val) ** (252 / days) - 1

#     # print them all
#     print(f"Final Portfolio Value: {end_val:,.2f}")
#     print(f"CAGR (approx): {cagr:.2%}")
#     print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
#     print(f"Max Drawdown: {max_dd:.2f}%")
#     print(f"Total Trades: {total_closed}")
#     print(f"Win Rate: {win_rate:.2%}")

#     # show the plot
#     cerebro.plot(style='candlestick')


# backtest.py

import os
import pandas as pd
import backtrader as bt
import yfinance as yf

# ─── Config ───────────────────────────────────────────────────────────────────
DATA_DIR     = 'data'
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals_1d.csv')  # or signals_3d.csv

START_CASH = 100_000
COMMISSION = 0.001

# ─── 1) Price fetch helper ────────────────────────────────────────────────────
def fetch_price_data(ticker, start, end):
    """
    Download OHLCV data for `ticker` between `start` and `end` using yfinance.
    Returns a DataFrame with lowercase ['open','high','low','close','volume'].
    """
    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    df = hist[['Open','High','Low','Close','Volume']].rename(columns=str.lower)
    df.dropna(inplace=True)
    return df

# ─── 2) Strategy ──────────────────────────────────────────────────────────────
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
        # Build mapping (date, ticker) -> signal
        sig = self.params.signal_df.copy()
        sig['timestamp'] = pd.to_datetime(sig['timestamp'], utc=True).dt.date
        sig = sig.drop_duplicates(subset=['timestamp','ticker'], keep='last')
        self.signal_map = sig.set_index(['timestamp','ticker'])['signal'].to_dict()

    def next(self):
        today = None
        # Iterate through each data feed
        for data in self.datas:
            dt     = data.datetime.date(0)
            if today is None:
                today = dt  # just for logging consistency
            ticker = data._name
            signal = self.signal_map.get((dt, ticker), "Neutral")
            pos    = self.getposition(data).size
            price  = data.close[0]

            # 1) If flat, enter on Long/Short
            if pos == 0 and signal in ("Long", "Short"):
                self.log(f'ENTER {signal} {ticker} @ {price:.2f}', dt)
                if signal == "Long":
                    self.buy(data=data)
                else:
                    self.sell(data=data)

            # 2) If in a position, close on opposite or Neutral
            elif pos != 0:
                if (pos > 0 and signal in ("Short", "Neutral")) or \
                   (pos < 0 and signal in ("Long",  "Neutral")):
                    self.log(f'EXIT  {ticker} @ {price:.2f} (sig={signal})', dt)
                    self.close(data=data)

    def stop(self):
        pnl = self.broker.getvalue() - START_CASH
        print(f'Ending Value: {self.broker.getvalue():.2f}, PnL: {pnl:.2f}')

# ─── 3) Run backtest ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    # 3a) load & shift signals by one day
    signals = pd.read_csv(SIGNALS_FILE)
    signals['timestamp'] = (
        pd.to_datetime(signals['timestamp'], utc=True)
          .dt.normalize()
          + pd.Timedelta(days=1)
    )

    # 3b) determine date range
    start = signals['timestamp'].min().date().isoformat()
    end   = (signals['timestamp'].max().date() + pd.Timedelta(days=1)).isoformat()

    # 3c) setup Cerebro
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(START_CASH)
    cerebro.broker.setcommission(commission=COMMISSION)

    # 3d) add each ticker’s data feed
    for ticker in signals['ticker'].unique():
        price_df = fetch_price_data(ticker, start, end)
        cerebro.adddata(bt.feeds.PandasData(dataname=price_df), name=ticker)

    # 3e) add strategy + analyzers
    cerebro.addstrategy(SignalStrategy, signal_df=signals, printlog=False)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio,   _name="sharpe",   timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown,      _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    # 3f) run once
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():,.2f}')
    results = cerebro.run()
    strat   = results[0]
    end_val = cerebro.broker.getvalue()

    print(strat.analyzers.sharpe.get_analysis())
    # 3g) extract metrics
    sharpe  = strat.analyzers.sharpe.get_analysis().get("sharperatio", float('nan'))
    max_dd  = strat.analyzers.drawdown.get_analysis().get("max", {}).get("drawdown", 0.0)
    trades  = strat.analyzers.trades.get_analysis().get("total", {}).get("closed", 0)
    won     = strat.analyzers.trades.get_analysis().get("won",   {}).get("total",  0)
    winrate = (won / trades) if trades else float('nan')
    days    = (pd.to_datetime(end) - pd.to_datetime(start)).days or 1
    cagr    = (end_val / START_CASH)**(252/days) - 1

    # 3h) print summary
    print(f'Final Portfolio Value: {end_val:,.2f}')
    print(f'CAGR (approx):           {cagr:.2%}')
    print(f'Sharpe Ratio:            {sharpe:.2f}')
    print(f'Max Drawdown:            {max_dd:.2f}%')
    print(f'Total Trades:            {trades}')
    print(f'Win Rate:                {winrate:.2%}')

    # 3i) plot
    cerebro.plot(style='candlestick')