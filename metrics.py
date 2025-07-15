from datetime import datetime

def summarize_performance(
    cerebro,
    strat,
    start_date: datetime.date,
    end_date: datetime.date,
    start_cash: float = 100_000,
) -> dict:
    """
    Extract CAGR, Sharpe, max drawdown, trade count, and win rate.
    """
    end_val = cerebro.broker.getvalue()
    days = (end_date - start_date).days or 1
    cagr = (end_val / start_cash)**(252/days) - 1

    sharpe  = None
    max_dd  = 0.0
    trades  = 0
    win_rate = None

    if strat is not None:
        # Sharpe
        analysis_sh = strat.analyzers.sharpe.get_analysis()
        sr = analysis_sh.get('sharperatio', None)
        sharpe = float(sr) if sr is not None else None
        # Drawdown
        dd_info = strat.analyzers.drawdown.get_analysis().get('max', {})
        max_dd  = dd_info.get('drawdown', 0.0)
        # Trades & win-rate
        ta       = strat.analyzers.trades.get_analysis().get('total', {})
        trades   = ta.get('closed', 0)
        won      = strat.analyzers.trades.get_analysis().get('won',{}).get('total',0)
        win_rate = (won / trades) if trades else None

    return {
        'cagr':    cagr,
        'sharpe':  sharpe,
        'max_dd':  max_dd,
        'trades':  trades,
        'win_rate': win_rate,
    }