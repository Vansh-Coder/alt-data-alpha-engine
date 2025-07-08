import os
import pandas as pd

# Directory & file paths
data_dir = "data"
scored_file = os.path.join(data_dir, "sentiment_scored.csv")
output_file = os.path.join(data_dir, "signals.csv")

# Signal thresholds
LONG_THRESHOLD = 0.1
SHORT_THRESHOLD = -0.1


def generate_signals(df: pd.DataFrame, window_days: int = 1,
                     agg_col: str = "SentimentScore",
                     signal_col: str = "signal") -> pd.DataFrame:
    """
    Compute rolling average sentiment over a time window per ticker,
    then assign Long/Short/Neutral signals.
    """
    # Copy & parse timestamp
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Function to roll per group using time index
    def roll_group(group):
        g = group.set_index("timestamp").sort_index()
        # Rolling mean over time window
        g["agg_score"] = g[agg_col].rolling(f"{window_days}d").mean()
        return g.reset_index()

    # Apply per ticker
    rolled = (
        df.groupby("ticker", group_keys=False)
          .apply(roll_group)
    )

    # Assign signals
    rolled[signal_col] = rolled["agg_score"].apply(
        lambda s: "Long" if s > LONG_THRESHOLD
        else ("Short" if s < SHORT_THRESHOLD else "Neutral")
    )

    return rolled[["timestamp", "ticker", "agg_score", signal_col]]


if __name__ == '__main__':
    # Load sentiment-scored data
    raw = pd.read_csv(scored_file)

    # Generate signals for 1-day and 3-day
    signals_1d = generate_signals(raw, window_days=1)
    signals_3d = generate_signals(raw, window_days=3)

    # Save individual
    signals_1d.to_csv(os.path.join(data_dir, "signals_1d.csv"), index=False)
    signals_3d.to_csv(os.path.join(data_dir, "signals_3d.csv"), index=False)

    # Combine with window label
    combined = pd.concat([
        signals_1d.assign(window='1d'),
        signals_3d.assign(window='3d')
    ], ignore_index=True)
    combined.to_csv(output_file, index=False)
    print(f"Signals generated and saved to {output_file}")