import os
import pandas as pd
import backtrader as bt
import yfinance as yf
from datetime import datetime

# Paths
DATA_DIR = 'data'
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals_1d.csv')  # 1-day signals file

# 1. Fetch and prepare price data

def fetch_price_data(ticker, start, end):
    """
    Download OHLCV data for `ticker` between `start` and `end` using yfinance Ticker.history,
    return DataFrame indexed by date with lowercase columns ['open','high','low','close','volume'].
    """
    # Use history() to get clean single-index columns
    try:
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch history for {ticker}: {e}")

    # Ensure required columns exist
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col not in hist.columns:
            raise ValueError(f"Missing '{col}' in price data for {ticker}")

    # Select and lowercase
    df = hist[['Open', 'High', 'Low', 'Close', 'Volume']].rename(columns=str.lower)
    # Drop any rows with NaNs
    df.dropna(inplace=True)
    return df
[['open', 'high', 'low', 'close', 'volume']]

# 2. Define strategy based on signals
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
        # Prepare a mapping of (date, ticker) -> signal
        sig = self.params.signal_df.copy()
        sig['timestamp'] = pd.to_datetime(sig['timestamp'], utc=True).dt.date
        sig = sig.drop_duplicates(subset=['timestamp', 'ticker'], keep='last')
        self.signal_map = sig.set_index(['timestamp', 'ticker'])['signal'].sort_index()
        self.dataclose = self.datas[0].close

    def next(self):
        dt = self.datas[0].datetime.date(0)
        ticker = self.datas[0]._name
        key = (dt, ticker)
        if key in self.signal_map:
            signal = self.signal_map.loc[key]
            pos = self.getposition(self.datas[0]).size
            price = self.dataclose[0]
            if signal == 'Long' and pos == 0:
                self.log(f'BUY CREATE {ticker}, {price:.2f}')
                self.buy()
            elif signal == 'Short' and pos == 0:
                self.log(f'SELL SHORT CREATE {ticker}, {price:.2f}')
                self.sell()
            elif signal == 'Neutral' and pos != 0:
                self.log(f'CLOSE POSITION {ticker}, {price:.2f}')
                self.close()

    def stop(self):
        pnl = round(self.broker.getvalue() - self.broker.startingcash, 2)
        print(f'Ending Value: {self.broker.getvalue():.2f}, PnL: {pnl}')

# 3. Run backtest
if __name__ == '__main__':
    # Load signals
    signals = pd.read_csv(SIGNALS_FILE)
    signals['timestamp'] = pd.to_datetime(signals['timestamp'], utc=True)

    # Determine date range (inclusive)
    start = signals['timestamp'].min().date().isoformat()
    end   = (signals['timestamp'].max().date() + pd.Timedelta(days=1)).isoformat()

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # Add data feeds for each ticker
    for ticker in signals['ticker'].unique():
        price_df = fetch_price_data(ticker, start, end)
        data_feed = bt.feeds.PandasData(dataname=price_df)
        cerebro.adddata(data_feed, name=ticker)

    cerebro.addstrategy(SignalStrategy, signal_df=signals, printlog=False)

    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    cerebro.run()
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
    cerebro.plot(style='candlestick')