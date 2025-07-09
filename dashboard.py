import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Paths to data files
data_dir = 'data'
signals_file = os.path.join(data_dir, 'signals_with_explanations.csv')
# Fallback to signals.csv if explanations not present
if not os.path.exists(signals_file):
    signals_file = os.path.join(data_dir, 'signals.csv')

# Load signals
df = pd.read_csv(signals_file, parse_dates=['timestamp'])

# If 'Explanation' not in df, set empty
def ensure_column(df, col):
    if col not in df.columns:
        df[col] = ''
    return df

df = ensure_column(df, 'Explanation')

# Sidebar controls
st.sidebar.title('Signal Explorer')
tickers = df['ticker'].unique().tolist()
selected_ticker = st.sidebar.selectbox('Ticker', tickers)

# Date slider
min_date = df['timestamp'].min().date()
max_date = df['timestamp'].max().date()
start_date, end_date = st.sidebar.slider(
    'Date range',
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Filtered data
mask = (
    (df['ticker'] == selected_ticker) &
    (df['timestamp'].dt.date >= start_date) &
    (df['timestamp'].dt.date <= end_date)
)
filtered = df.loc[mask].sort_values('timestamp')

# Main page
st.title(f"📊 Sentiment Signals Dashboard: {selected_ticker}")

st.markdown(f"**Date range:** {start_date} to {end_date}")

# Plot aggregated sentiment scores
st.subheader('Rolling Sentiment Score (agg_score)')
if not filtered.empty:
    score_ts = filtered.set_index('timestamp')['agg_score']
    st.line_chart(score_ts)
else:
    st.write('No data for this ticker in the selected date range.')

# Show signals table
st.subheader('Signals Table')
st.dataframe(
    filtered[['timestamp', 'agg_score', 'signal', 'Explanation']]
)

# Show recent explanations
st.subheader('Recent Explanations')
for idx, row in filtered.tail(5).iterrows():
    ts = row['timestamp'].strftime('%Y-%m-%d %H:%M')
    st.markdown(f"- **{ts}**: {row['signal']}  \n  *{row['Explanation']}*")

# Footer
st.write('---')
st.write('Data powered by AI-driven sentiment signals and backtesting pipeline.')