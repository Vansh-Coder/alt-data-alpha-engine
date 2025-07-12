import os
import itertools
import pandas as pd
import numpy as np
import backtest   # your backtest.py with run_backtest(signals_df, sl, tp, price_cache)
from datetime import timedelta

# ─── Hyper‐parameter grids ─────────────────────────────────────────────────────
WINDOWS    = [5]
QOPTS      = [0.025, 0.05, 0.075]
SL_PCTS    = [0.02, 0.0225, 0.025]
TP_PCTS    = [0.04, 0.045, 0.05]

SIG_FILES = {
    1: 'data/signals_1d.csv',
    3: 'data/signals_3d.csv',
    5: 'data/signals_5d.csv'
}

# ─── 1) Build price_cache once ────────────────────────────────────────────────
all_sigs = []
for fn in SIG_FILES.values():
    tmp = pd.read_csv(fn, parse_dates=['timestamp'])
    all_sigs.append(tmp[['timestamp','ticker']])
all_sigs = pd.concat(all_sigs, ignore_index=True)

start_dt = all_sigs['timestamp'].min().date().isoformat()
end_dt   = (all_sigs['timestamp'].max().date() + timedelta(days=1)).isoformat()

price_cache = {
    t: backtest.fetch_price_data(t, start_dt, end_dt)
    for t in all_sigs['ticker'].unique()
}

# ─── 2) Screen out low‐edge tickers by standalone Sharpe ──────────────────────
baseline = pd.read_csv(SIG_FILES[3]).dropna(subset=['agg_score'])
ticker_sharpes = {}
for tk, grp in baseline.groupby('ticker'):
    p10 = grp['agg_score'].quantile(0.10)
    p90 = grp['agg_score'].quantile(0.90)
    tmp = grp.copy()
    tmp['signal'] = tmp['agg_score'].apply(
        lambda s: 'Long' if s >= p90 else ('Short' if s <= p10 else 'Neutral')
    )
    perf = backtest.run_backtest(tmp, 0.0225, 0.045, price_cache)
    ticker_sharpes[tk] = perf.get('sharpe') or np.nan

sorted_t = sorted(
    ticker_sharpes.items(),
    key=lambda kv: np.nan_to_num(kv[1], -np.inf),
    reverse=True
)
keep = int(len(sorted_t) * 0.8)
good_tickers = {t for t,_ in sorted_t[:keep]}
print(f"Screened tickers: {len(sorted_t)} -> {len(good_tickers)} kept")

# ─── 3) Grid search (with conviction sizing) ─────────────────────────────────
results = []
for window, sl, tp, ql, qh in itertools.product(
    WINDOWS, SL_PCTS, TP_PCTS, QOPTS, QOPTS
):
    if ql >= qh:
        continue

    # load & restrict
    df = pd.read_csv(SIG_FILES[window], parse_dates=['timestamp'])
    df = df[df['ticker'].isin(good_tickers)].copy()

    # per‐ticker low/high percentiles
    percs = (
        df.groupby('ticker')['agg_score']
          .quantile([ql, qh])
          .unstack()
          .rename(columns={ql: 'p_low', qh: 'p_high'})
    )
    df = df.merge(percs, left_on='ticker', right_index=True)

    # conviction factor: abs((agg_score – p_low)/(p_high – p_low)), capped at 1
    df['conv'] = (
        (df['agg_score'] - df['p_low']) 
         .div(df['p_high'] - df['p_low'])
         .abs()
         .clip(upper=1.0)
    )
    # fill nan values with 0 caused above when p_high == p_low
    df['conv'] = df['conv'].fillna(0.0)

    # generate signals
    df['signal'] = df.apply(
        lambda r: 'Long'  if r['agg_score'] >= r['p_high'] * qh
                  else ('Short' if r['agg_score'] <= r['p_low'] * ql else 'Neutral'),
        axis=1
    )

    # sanity check:
    assert 'conv' in df.columns, "🔴 conv column missing!"

    perf = backtest.run_backtest(df, sl, tp, price_cache)

    entry = {
        'window':       window,
        'q_low':        ql,
        'q_high':       qh,
        'stop_loss':    sl,
        'take_profit':  tp,
        'signal_count': int((df['signal'] != 'Neutral').sum())
    }
    entry.update(perf)
    results.append(entry)

    s = perf['sharpe'] or 0.0
    print(f"W={window}  Q=({ql:.3f},{qh:.3f})  SL={sl:.4f}  TP={tp:.4f}  → Sharpe {s:.4f}")

# ─── 4) Report top 10 ─────────────────────────────────────────────────────────
out = pd.DataFrame(results)
os.makedirs('data', exist_ok=True)
out.to_csv('data/grid_search_with_conviction.csv', index=False)

print("\nTop 10 by Sharpe:")
print(out.sort_values('sharpe', ascending=False).head(10).to_string(index=False))