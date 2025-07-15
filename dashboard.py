import pandas as pd
import streamlit as st
import altair as alt

# ─── Helper ───────────────────────────────────────────────────────────────────

@st.cache_data
def load_signals_data() -> pd.DataFrame:
    """
    Load the combined signals.csv with columns:
      timestamp, ticker, agg_score, signal, (and optional window)
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
    d = df[df["ticker"] == ticker]
    avg = d["agg_score"].mean() if not d.empty else float("nan")
    cnt = int((d["signal"] != "Neutral").sum())
    c1, c2 = st.columns(2)
    c1.metric("Avg. Sentiment", f"{avg:.3f}")
    c2.metric("Total Signals", f"{cnt}")

def render_time_series(filtered: pd.DataFrame):
    """
    Line + colored points of sentiment over time.
    """
    base = alt.Chart(filtered).encode(
        x=alt.X("timestamp:T", title="Date"),
        y=alt.Y("agg_score:Q", title="Sentiment Score")
    )
    line = base.mark_line()
    points = base.mark_point(filled=True, size=60).encode(
        color=alt.Color(
            "signal:N",
            scale=alt.Scale(domain=["Long","Short"], range=["green","red"])
        )
    )
    chart = (line + points).properties(
        height=300,
        title="Sentiment & Signals Over Time"
    ).interactive()
    st.altair_chart(chart, use_container_width=True)

# ─── Main ─────────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Signal Explorer")
st.title("📊 Sentiment Signals Dashboard")

# Load all signals
df_all = load_signals_data()

# Ticker selector
tickers = sorted(df_all["ticker"].unique())
ticker  = st.sidebar.selectbox("Select Ticker", tickers)

# Filter for this ticker
df_ticker = df_all[df_all["ticker"] == ticker]

# Per‐ticker date slider
min_date = df_ticker["timestamp"].dt.date.min()
max_date = df_ticker["timestamp"].dt.date.max()
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
].sort_values("timestamp")

# Render KPI cards and chart
render_kpis(df_all, ticker)
st.markdown("---")

if not filtered.empty:
    render_time_series(filtered)
else:
    st.write("No sentiment data in this range.")

st.markdown("---")
st.markdown("🔧 *Powered by AI-driven sentiment signals*")