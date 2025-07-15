# import streamlit as st
# import pandas as pd
# import os
# from datetime import datetime

# # Paths to data files
# data_dir = 'data'
# signals_file = os.path.join(data_dir, 'signals_with_explanations.csv')
# # Fallback to signals.csv if explanations not present
# if not os.path.exists(signals_file):
#     signals_file = os.path.join(data_dir, 'signals.csv')

# # Load signals
# df = pd.read_csv(signals_file, parse_dates=['timestamp'])

# # If 'Explanation' not in df, set empty
# def ensure_column(df, col):
#     if col not in df.columns:
#         df[col] = ''
#     return df

# df = ensure_column(df, 'Explanation')

# # Sidebar controls
# st.sidebar.title('Signal Explorer')
# tickers = df['ticker'].unique().tolist()
# selected_ticker = st.sidebar.selectbox('Ticker', tickers)

# # Date slider
# min_date = df['timestamp'].min().date()
# max_date = df['timestamp'].max().date()
# start_date, end_date = st.sidebar.slider(
#     'Date range',
#     min_value=min_date,
#     max_value=max_date,
#     value=(min_date, max_date),
#     format="YYYY-MM-DD"
# )

# # Filtered data
# mask = (
#     (df['ticker'] == selected_ticker) &
#     (df['timestamp'].dt.date >= start_date) &
#     (df['timestamp'].dt.date <= end_date)
# )
# filtered = df.loc[mask].sort_values('timestamp')

# # Main page
# st.title(f"📊 Sentiment Signals Dashboard: {selected_ticker}")

# st.markdown(f"**Date range:** {start_date} to {end_date}")

# # Plot aggregated sentiment scores
# st.subheader('Rolling Sentiment Score (agg_score)')
# if not filtered.empty:
#     score_ts = filtered.set_index('timestamp')['agg_score']
#     st.line_chart(score_ts)
# else:
#     st.write('No data for this ticker in the selected date range.')

# # Show signals table
# st.subheader('Signals Table')
# st.dataframe(
#     filtered[['timestamp', 'agg_score', 'signal', 'Explanation']]
# )

# # Show recent explanations
# st.subheader('Recent Explanations')
# for idx, row in filtered.tail(5).iterrows():
#     ts = row['timestamp'].strftime('%Y-%m-%d %H:%M')
#     st.markdown(f"- **{ts}**: {row['signal']}  \n  *{row['Explanation']}*")

# # Footer
# st.write('---')
# st.write('Data powered by AI-driven sentiment signals and backtesting pipeline.')
# dashboard.py
# dashboard.py

import os
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime

# ─── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR           = "data"
SIG_EXPL_FILE      = os.path.join(DATA_DIR, "signals_with_explanations.csv")
SIG_FILE           = os.path.join(DATA_DIR, "signals.csv")
PERF_FILE          = os.path.join(DATA_DIR, "performance_per_ticker.csv")
EQUITY_TMPL        = os.path.join(DATA_DIR, "equity_{ticker}.csv")

# ─── Load signals & explanations ───────────────────────────────────────────────
# Prefer the explanations file if it exists, otherwise fall back
signals_path = SIG_EXPL_FILE if os.path.exists(SIG_EXPL_FILE) else SIG_FILE
df = pd.read_csv(signals_path, parse_dates=["timestamp"])

# Ensure we have a 'signal' column: merge it in if missing
if "signal" not in df.columns:
    df_orig = pd.read_csv(SIG_FILE, parse_dates=["timestamp"])
    df = df.merge(
        df_orig[["timestamp", "ticker", "signal"]],
        on=["timestamp", "ticker"],
        how="left"
    )
    df["signal"] = df["signal"].fillna("Neutral")

# Ensure an Explanation column always exists
if "Explanation" not in df.columns:
    df["Explanation"] = ""

# ─── Sidebar filters ──────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Signal Explorer")
tickers = sorted(df["ticker"].unique())
selected_ticker = st.sidebar.selectbox("Select Ticker", tickers)

min_date = df["timestamp"].dt.date.min()
max_date = df["timestamp"].dt.date.max()
start_date, end_date = st.sidebar.slider(
    "Date range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD",
)

# ─── Filtered DataFrame ───────────────────────────────────────────────────────
mask = (
    (df["ticker"] == selected_ticker)
    & (df["timestamp"].dt.date >= start_date)
    & (df["timestamp"].dt.date <= end_date)
)
filtered = df.loc[mask].sort_values("timestamp")
signals_only = filtered[filtered["signal"] != "Neutral"]

# ─── Title & KPIs ─────────────────────────────────────────────────────────────
st.title(f"📊 Sentiment Signals Dashboard — {selected_ticker}")
st.markdown(f"**Date range:** {start_date} → {end_date}")

# Compute KPIs
avg_score   = filtered["agg_score"].mean() if not filtered.empty else float("nan")
num_signals = len(signals_only)

# Attempt to load per-ticker performance
perf_exists = os.path.exists(PERF_FILE)
sharpe = cagr = win_rate = None
if perf_exists:
    perf_df = pd.read_csv(PERF_FILE)
    perf_row = perf_df[perf_df["ticker"] == selected_ticker]
    if not perf_row.empty:
        sharpe   = float(perf_row["sharpe"].iloc[0])
        cagr     = float(perf_row["cagr"].iloc[0])
        win_rate = float(perf_row["win_rate"].iloc[0])

# Display metric cards
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Avg. Sentiment", f"{avg_score:.3f}")
col2.metric("Total Signals", f"{num_signals}")
col3.metric(
    "Sharpe Ratio",
    f"{sharpe:.2f}" if sharpe is not None else "n/a",
    delta="⚠️ Low" if (sharpe is not None and sharpe < 0.1) else None,
    delta_color="inverse" if (sharpe is not None and sharpe < 0.1) else "normal",
)
col4.metric("CAGR", f"{cagr:.2%}" if cagr is not None else "n/a")
col5.metric("Win Rate", f"{win_rate:.2%}" if win_rate is not None else "n/a")

st.markdown("---")

# ─── Sentiment Time Series with Signal Markers ────────────────────────────────
if not filtered.empty:
    base = alt.Chart(filtered).encode(
        x=alt.X("timestamp:T", title="Date"),
        y=alt.Y("agg_score:Q", title="Sentiment Score")
    )
    line = base.mark_line(color="steelblue")
    points = base.mark_point(filled=True, size=60).encode(
        color=alt.Color(
            "signal:N",
            scale=alt.Scale(domain=["Long", "Short"], range=["green", "red"])
        )
    )
    chart = (line + points).properties(
        width=700, height=300, title="Sentiment & Signals Over Time"
    ).interactive()
    st.altair_chart(chart, use_container_width=True)
else:
    st.write("No sentiment data in this range.")

# ─── Signal Distribution by Month ─────────────────────────────────────────────
st.subheader("📈 Signal Count by Month")
if not signals_only.empty:
    signals_only = signals_only.assign(
        month=signals_only["timestamp"].dt.to_period("M").dt.to_timestamp()
    )
    hist = (
        alt.Chart(signals_only)
        .mark_bar()
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("count()", title="Number of Signals"),
            color=alt.Color("signal:N", scale=alt.Scale(range=["green", "red"]))
        )
        .properties(width=700, height=200)
    )
    st.altair_chart(hist, use_container_width=True)
else:
    st.write("No Long/Short signals to display.")

# ─── Signals & Explanations Table ────────────────────────────────────────────
st.subheader("🗂️ Signals & Explanations")
st.dataframe(
    filtered[["timestamp", "agg_score", "signal", "Explanation"]]
    .rename(columns={
        "timestamp":   "Timestamp",
        "agg_score":   "Score",
        "signal":      "Signal",
        "Explanation": "Rationale"
    }),
    use_container_width=True
)

# ─── Advanced Metrics (if available) ─────────────────────────────────────────
if perf_exists:
    with st.expander("🔎 Advanced Metrics per Ticker"):
        st.write("Backtest performance summary:")
        display = perf_df.set_index("ticker").loc[[selected_ticker]]
        def _highlight_low(sh):
            return "background-color:salmon" if sh < 0.1 else ""
        styled = (
            display.style
            .format({"sharpe":"{:.2f}", "cagr":"{:.2%}", "max_dd":"{:.2f}", "win_rate":"{:.2%}"})
            .applymap(_highlight_low, subset=["sharpe"])
        )
        st.dataframe(styled, use_container_width=True)
else:
    st.info("Advanced performance metrics not found; enable performance_per_ticker.csv to see them.")

# ─── Equity Curve (optional) ───────────────────────────────────────────────────
equity_path = EQUITY_TMPL.format(ticker=selected_ticker)
if os.path.exists(equity_path):
    st.subheader("💹 Equity Curve")
    eq = pd.read_csv(equity_path, parse_dates=["timestamp"])
    eq = eq[(eq["timestamp"].dt.date >= start_date) & (eq["timestamp"].dt.date <= end_date)]
    st.line_chart(eq.set_index("timestamp")["equity"])
else:
    st.write("Equity curve file not found; skipping.")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "🔧 *Powered by AI-driven sentiment signals*, "
    "*with risk management, conviction sizing, and backtested performance.*"
)