import os
import itertools
import pandas as pd
from datetime import timedelta

from backtest import run_backtest, fetch_price_data
from signals import load_signals, add_conviction_signals, screen_tickers
from metrics import summarize_performance

# ─── Hyperparameter grids ─────────────────────────────────────────────────
WINDOWS  = [1, 3, 5]
QOPTS    = [0.025, 0.05, 0.075]
SL_PCTS  = [0.02, 0.0225, 0.025]
TP_PCTS  = [0.04, 0.045, 0.05]

# ─── File map for pre‑saved signals ──────────────────────────────────────────
SIG_FILES = {
    1: 'data/signals_1d.csv',
    3: 'data/signals_3d.csv',
    5: 'data/signals_5d.csv'
}

# 1) Build a shared price cache (so we don’t re‑download every backtest)
all_sigs = []
for fn in SIG_FILES.values():
    tmp = pd.read_csv(fn, parse_dates=['timestamp'])
    all_sigs.append(tmp[['timestamp','ticker']])
all_sigs = pd.concat(all_sigs, ignore_index=True)
start_dt = all_sigs['timestamp'].min().date().isoformat()
end_dt   = (all_sigs['timestamp'].max().date() + timedelta(days=1)).isoformat()

price_cache = {
    t: fetch_price_data(t, start_dt, end_dt)
    for t in all_sigs['ticker'].unique()
}

# 2) Screen tickers using standalone 3‑day signals
baseline = pd.read_csv(SIG_FILES[3], parse_dates=['timestamp'])
good_tickers = screen_tickers(
    baseline,
    stop_loss_pct=0.0225,
    take_profit_pct=0.045,
    price_cache=price_cache,
    min_sharpe=0.0
)
print(f"Screened tickers: {len(baseline['ticker'].unique())} → {len(good_tickers)} kept")

# 3) Grid search over (window, SL, TP, q_low, q_high)
results = []
for window, sl, tp, ql, qh in itertools.product(
    WINDOWS, SL_PCTS, TP_PCTS, QOPTS, QOPTS
):
    if ql >= qh:
        continue

    # 3.1) Load the pre‑saved signals for this window
    df = load_signals(window)
    df = df[df['ticker'].isin(good_tickers)].copy()

    # 3.2) Add conviction‐based signals
    df = add_conviction_signals(df, ql, qh)

    # 3.3) Run the backtest & summarize
    cerebro, strat, start_date, end_date = run_backtest(
        df, stop_loss=sl, take_profit=tp, external_price_cache=price_cache
    )
    perf = summarize_performance(cerebro, strat, start_date, end_date)

    results.append({
        'window':      window,
        'q_low':       ql,
        'q_high':      qh,
        'stop_loss':   sl,
        'take_profit': tp,
        'signal_count': int((df['signal'] != 'Neutral').sum()),
        **perf
    })

    print(f"W={window}  Q=({ql:.3f},{qh:.3f})  SL={sl:.4f}  TP={tp:.4f} → Sharpe {perf['sharpe']:.4f}")

# 4) Save and show top 10 by Sharpe
out = pd.DataFrame(results)
os.makedirs('data', exist_ok=True)
out.to_csv('data/grid_search_with_conviction.csv', index=False)

print("\nTop 10 by Sharpe:")
print(out.sort_values('sharpe', ascending=False).head(10).to_string(index=False))