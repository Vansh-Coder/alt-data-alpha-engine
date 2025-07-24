import pandas as pd
import streamlit as st
import altair as alt

# ─── Helper ───────────────────────────────────────────────────────────────────

@st.cache_data
def load_signals_data() -> pd.DataFrame:
    """
    Load the combined signals.csv with columns:
      timestamp, ticker, agg_score, signal, (optional window)
    """
    path = "data/signals.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])
    if "signal" not in df.columns:
        df["signal"] = "Neutral"
    return df

# ─── Rendering functions ──────────────────────────────────────────────────────

def render_kpis(df: pd.DataFrame, ticker: str):
    """
    Display average sentiment & total trade signals for a ticker.
    """
    d   = df[df["ticker"] == ticker]
    avg = d["agg_score"].mean() if not d.empty else float("nan")
    cnt = int((d["signal"] != "Neutral").sum())
    c1, c2 = st.columns(2)
    c1.metric("Avg. Sentiment", f"{avg:.3f}")
    c2.metric("Total Signals",   f"{cnt}")

# ─── Main ─────────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Signal Explorer")
st.title("📊 Sentiment Signals Dashboard")

# Load & filter
df_all = load_signals_data()

tickers = sorted(df_all["ticker"].unique())
ticker  = st.sidebar.selectbox("Select Ticker", tickers)

# Date range based on that ticker alone
df_ticker = df_all[df_all["ticker"] == ticker]
min_date  = df_ticker["timestamp"].dt.date.min()
max_date  = df_ticker["timestamp"].dt.date.max()
start_date, end_date = st.sidebar.slider(
    "Date range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Apply date filter
filtered = df_ticker[
    (df_ticker["timestamp"].dt.date >= start_date) &
    (df_ticker["timestamp"].dt.date <= end_date)
]

# KPI cards
render_kpis(df_all, ticker)
st.markdown("---")

if not filtered.empty:
    # ─── Hourly aggregation ────────────────────────────────
    df_hourly = (
        filtered
        .set_index("timestamp")
        .resample("1h")
        .agg(
            avg_score    = ("agg_score", "mean"),
            signal_count = ("signal", lambda s: (s != "Neutral").sum())
        )
        .dropna(subset=["avg_score"])
        .reset_index()
    )

    # ─── Average Sentiment Line ────────────────────────────
    line = (
        alt.Chart(df_hourly)
        .mark_line(point=True)
        .encode(
            x=alt.X("timestamp:T", title="Hour"),
            y=alt.Y("avg_score:Q", title="Avg. Sentiment"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Timestamp"),
                alt.Tooltip("avg_score:Q", title="Avg Sentiment", format=".3f"),
                alt.Tooltip("signal_count:Q", title="Signal Count")
            ]
        )
        .properties(height=200, title="Hourly Avg. Sentiment")
    )

    # ─── Signal Count Bar ──────────────────────────────────
    bar = (
        alt.Chart(df_hourly)
        .mark_bar(opacity=0.3)
        .encode(
            x="timestamp:T",
            y=alt.Y("signal_count:Q", title="Signal Count"),
        )
        .properties(height=100, title="Signals per Hour")
    )

    # ─── Combine & Render ──────────────────────────────────
    chart = alt.vconcat(line, bar).configure_axis(grid=False)
    st.altair_chart(chart, use_container_width=True)

else:
    st.write("No sentiment data in this range.")

st.markdown("---")
st.markdown("🔧 *Powered by AI-driven sentiment signals*")
