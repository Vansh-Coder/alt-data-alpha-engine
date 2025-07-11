# grid_search.py

import itertools
import pandas as pd
import numpy as np
import backtest   # now includes run_backtest(signals_df, sl, tp, price_cache)
from datetime import timedelta
import time

start_time = time.time()

# ─── Hyper‐parameter grids ─────────────────────────────────────────────────────
WINDOWS      = [5]
QOPTS        = [0.025, 0.05, 0.075]
CONV_MULS    = [0.5, 1.0, 1.5]
SL_PCTS      = [0.02, 0.0225, 0.025]
TP_PCTS      = [0.04, 0.045, 0.05]
START_CASH   = 100_000

SIG_FILES    = {
    1: 'data/signals_1d.csv',
    3: 'data/signals_3d.csv',
    5: 'data/signals_5d.csv'
}

# ─── Build global date range and cache all tickers once ───────────────────────
all_sigs = []
for fn in SIG_FILES.values():
    tmp = pd.read_csv(fn, parse_dates=['timestamp'])
    all_sigs.append(tmp[['timestamp','ticker']])
all_sigs = pd.concat(all_sigs, ignore_index=True)

min_date = all_sigs['timestamp'].min().date()
max_date = all_sigs['timestamp'].max().date() + pd.Timedelta(days=1)
start_dt = min_date.isoformat()
end_dt   = max_date.isoformat()

# Pre-fetch price history for every ticker
price_cache = {
    t: backtest.fetch_price_data(t, start_dt, end_dt)
    for t in all_sigs['ticker'].unique()
}

# ─── 1) Screen out low-edge tickers ─────────────────────────────────────────────
baseline = pd.read_csv(SIG_FILES[3]).dropna(subset=['agg_score'])
ticker_sharpes = {}
for ticker, grp in baseline.groupby('ticker'):
    p10 = grp['agg_score'].quantile(0.10)
    p90 = grp['agg_score'].quantile(0.90)
    grp['signal'] = grp['agg_score'].apply(
        lambda s: 'Long' if s>=p90 else ('Short' if s<=p10 else 'Neutral')
    )
    perf = backtest.run_backtest(grp, 0.0225, 0.04, price_cache)
    sh = perf.get('sharpe') or np.nan
    ticker_sharpes[ticker] = sh

sorted_t = sorted(
    ticker_sharpes.items(),
    key=lambda kv: np.nan_to_num(kv[1], -np.inf),
    reverse=True
)
keep = int(len(sorted_t)*0.8)
good_tickers = {t for t,_ in sorted_t[:keep]}
print(f"Screened tickers: {len(sorted_t)} -> {len(good_tickers)} kept")

# ─── 2) Main grid search with per-ticker / trailing stop / conviction ─────────
results = []
for window, sl, tp, ql, qh, cm, sm in itertools.product(
    WINDOWS, SL_PCTS, TP_PCTS, QOPTS, QOPTS, CONV_MULS, CONV_MULS
):
    if ql >= qh:
        continue

    df = pd.read_csv(SIG_FILES[window]).dropna(subset=['agg_score'])
    df = df[df['ticker'].isin(good_tickers)]

    # per-ticker tails
    percs = (
        df.groupby('ticker')['agg_score']
          .quantile([ql, qh])
          .unstack()
          .rename(columns={ql: 'p_low', qh: 'p_high'})
    )
    df = df.merge(percs, left_on='ticker', right_index=True)

    # conviction sizing
    df['conv'] = (df['agg_score'] - df['p_low']) / (df['p_high'] - df['p_low'])
    df['conv'] = df['conv'].abs()

    # signals
    df['signal'] = df.apply(
        lambda r: 'Long' if r['agg_score']>=r['p_high']*qh
                  else ('Short' if r['agg_score']<=r['p_low']*ql else 'Neutral'),
        axis=1
    )

    perf = backtest.run_backtest(df, sl, tp, price_cache)
    entry = {
        'window': window,
        'q_low': ql, 'q_high': qh,
        'conv_low': sm, 'conv_high': cm,
        'stop_loss': sl, 'take_profit': tp,
        'signal_count': int((df['signal']!='Neutral').sum())
    }
    entry.update(perf)
    results.append(entry)

    s = perf['sharpe']
    print(f"W={window} Q=({ql},{qh}) SL={sl:.3f} TP={tp:.3f} -> Sharpe {s:.2f}")

out = pd.DataFrame(results)
out.to_csv('grid_search_refined.csv', index=False)

print("\nTop 10 by Sharpe:")
print(out.sort_values('sharpe', ascending=False).head(10).to_string(index=False))

end_time = time.time()
elapsed_time = end_time - start_time

mins, secs = divmod(elapsed_time, 60)
print(f"Total time taken: {int(mins)}m {secs:.2f}s")