import os
import pandas as pd

# Paths
data_dir = "data"
scored_file = os.path.join(data_dir, "sentiment_scored.csv")
output_file = os.path.join(data_dir, "signals.csv")

# Thresholds
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

    # Helper: roll for one group
    def roll_group(group):
        g = group.set_index("timestamp").sort_index()
        g["agg_score"] = g[agg_col].rolling(f"{window_days}d").mean()
        return g.reset_index()

    # Apply manually per ticker to avoid FutureWarning
    frames = []
    for ticker, group in df.groupby("ticker"):
        rolled = roll_group(group)
        rolled["ticker"] = ticker
        frames.append(rolled)
    rolled_df = pd.concat(frames, ignore_index=True)

    # Signal mapping
    rolled_df[signal_col] = rolled_df["agg_score"].apply(
        lambda s: "Long" if s > LONG_THRESHOLD else ("Short" if s < SHORT_THRESHOLD else "Neutral")
    )

    return rolled_df[["timestamp", "ticker", "agg_score", signal_col]]


if __name__ == '__main__':
    raw = pd.read_csv(scored_file)

    signals_1d = generate_signals(raw, window_days=1)
    signals_3d = generate_signals(raw, window_days=3)

    # Save individual windows
    signals_1d.to_csv(os.path.join(data_dir, "signals_1d.csv"), index=False)
    signals_3d.to_csv(os.path.join(data_dir, "signals_3d.csv"), index=False)

    # Combined
    combined = pd.concat([
        signals_1d.assign(window='1d'),
        signals_3d.assign(window='3d')
    ], ignore_index=True)
    combined.to_csv(output_file, index=False)
    print(f"Signals generated and saved to {output_file}")