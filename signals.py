import os
import pandas as pd
from backtest import run_backtest
from metrics import summarize_performance

# Thresholds for basic rolling signals
LONG_THRESHOLD = 0.1
SHORT_THRESHOLD = -0.1

def generate_signals(df: pd.DataFrame, window_days: int = 1,
                     agg_col: str = "SentimentScore",
                     signal_col: str = "signal") -> pd.DataFrame:
    """
    Compute rolling average sentiment over a time window per ticker,
    then assign Long/Short/Neutral signals.
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    def roll_group(group):
        g = group.set_index("timestamp").sort_index()
        g["agg_score"] = g[agg_col].rolling(f"{window_days}d").mean()
        return g.reset_index()

    frames = []
    for ticker, group in df.groupby("ticker"):
        rolled = roll_group(group)
        rolled["ticker"] = ticker
        frames.append(rolled)
    rolled_df = pd.concat(frames, ignore_index=True)

    rolled_df[signal_col] = rolled_df["agg_score"].apply(
        lambda s: "Long" if s > LONG_THRESHOLD
                  else ("Short" if s < SHORT_THRESHOLD else "Neutral")
    )
    return rolled_df[["timestamp", "ticker", "agg_score", signal_col]]


def add_conviction_signals(df: pd.DataFrame, q_low: float, q_high: float) -> pd.DataFrame:
    """
    Add per-ticker percentile thresholds, compute conviction factor, and assign new signals.
    """
    df = df.copy()
    # Compute low/high percentiles per ticker
    percs = (
        df.groupby("ticker")["agg_score"]
          .quantile([q_low, q_high])
          .unstack()
          .rename(columns={q_low: "p_low", q_high: "p_high"})
    )
    df = df.merge(percs, left_on="ticker", right_index=True)

    # Conviction: normalized distance from midpoint, capped at 1
    df["conv"] = (
        (df["agg_score"] - df["p_low"])
         .div(df["p_high"] - df["p_low"])
         .abs()
         .clip(upper=1.0)
    ).fillna(0.0)

    # New signal based on percentiles
    df["signal"] = df.apply(
        lambda r: "Long"  if r["agg_score"] >= r["p_high"]
                  else ("Short" if r["agg_score"] <= r["p_low"] else "Neutral"),
        axis=1
    )
    return df


def screen_tickers(
    signals_df: pd.DataFrame,
    stop_loss_pct: float,
    take_profit_pct: float,
    price_cache: dict = None,
    min_sharpe: float = 0.0
) -> list:
    """
    Screen out tickers whose standalone backtest Sharpe is below min_sharpe.
    """
    keep = []
    for ticker, grp in signals_df.groupby("ticker"):
        cerebro, strat, start_date, end_date = run_backtest(
            grp[["timestamp", "ticker", "signal"]],
            stop_loss_pct,
            take_profit_pct,
            external_price_cache=price_cache
        )
        perf = summarize_performance(cerebro, strat, start_date, end_date)
        sharpe = perf.get("sharpe")
        if sharpe is not None and sharpe >= min_sharpe:
            keep.append(ticker)
    return keep


def load_sentiment(path="data/sentiment_scored.csv") -> pd.DataFrame:
    """Load your cleaned & scored DataFrame."""
    return pd.read_csv(path, parse_dates=["timestamp"])


def load_signals(window: int, dir: str = "data") -> pd.DataFrame:
    """
    Load the previously saved signals_{window}d.csv file.
    """
    path = os.path.join(dir, f"signals_{window}d.csv")
    return pd.read_csv(path, parse_dates=["timestamp"])


def save_all_signals(
    windows=(1, 3, 5),
    sentiment_path="data/sentiment_scored.csv",
    out_dir="data"
):
    """
    Compute signals for each window and save:
      data/signals_1d.csv, signals_3d.csv, signals_5d.csv
    """
    df = load_sentiment(sentiment_path)
    os.makedirs(out_dir, exist_ok=True)

    for w in windows:
        sig = generate_signals(df, window_days=w)
        filepath = os.path.join(out_dir, f"signals_{w}d.csv")
        sig.to_csv(filepath, index=False)
        print(f"Saved {filepath}")


if __name__ == "__main__":
    save_all_signals()