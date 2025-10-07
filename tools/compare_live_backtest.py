#!/usr/bin/env python3
"""Compare live signals to realistic backtest metrics for a single symbol.

Usage: python3 tools/compare_live_backtest.py --symbol WIFI.JK --start 2024-01-01 --cash 1000000
"""
import argparse
from fetch_data import load_ohlcv
from indicators import calculate_indicators
from trading_strategies import LiveSignalStrategy, BacktestStrategy
import realistic_backtest as rb


def summarize_live_signal(signal: dict) -> dict:
    if not signal or signal.get('signal') != 'BUY':
        return {'signal': signal.get('signal', 'HOLD')}

    entry = signal.get('entry_price')
    sl = signal.get('stop_loss')
    tp = signal.get('take_profit')
    shares = signal.get('shares', 0)
    investment = signal.get('investment', 0)
    risk_amount = signal.get('risk_amount', 0)
    risk_pct = signal.get('risk_percent', 0)

    tp_return_pct = ((tp / entry) - 1) * 100 if entry and tp else None
    sl_return_pct = ((sl / entry) - 1) * 100 if entry and sl else None

    return {
        'signal': 'BUY',
        'entry_price': entry,
        'stop_loss': sl,
        'take_profit': tp,
        'shares': shares,
        'investment': investment,
        'risk_amount': risk_amount,
        'risk_pct': risk_pct,
        'tp_return_pct': tp_return_pct,
        'sl_return_pct': sl_return_pct,
    }


def compare(symbol: str, start: str, cash: float):
    print(f"Loading data for {symbol} from {start}...")
    df = load_ohlcv(symbol, start)
    df = calculate_indicators(df)

    latest = df.iloc[-1]

    strategies = [
        ('BREAKOUT', LiveSignalStrategy.generate_breakout_signal, BacktestStrategy.has_breakout_signal),
        ('RESISTANCE_RETEST', LiveSignalStrategy.generate_resistance_retest_signal, BacktestStrategy.has_resistance_retest_signal),
        ('PULLBACK', LiveSignalStrategy.generate_pullback_signal, BacktestStrategy.has_pullback_signal),
    ]

    print('\nRunning realistic backtests (may take a moment)...')
    bt_results = {}
    for name, _, _ in strategies:
        try:
            _, total_return, max_dd, sharpe = rb.run_realistic_backtest(df.copy(), name, cash)
            bt_results[name] = {'total_return': total_return, 'max_dd': max_dd, 'sharpe': sharpe}
        except Exception as e:
            bt_results[name] = {'error': str(e)}

    print('\nLive vs Backtest Comparison:')
    print('-' * 80)
    for name, gen_fn, backtest_has in strategies:
        live_sig = gen_fn(df, symbol, cash)
        summary = summarize_live_signal(live_sig)

        # Did backtest logic detect a signal on the latest bar?
        backtest_flag = backtest_has(latest)

        print(f"Strategy: {name}")
        print(f"  Backtest (total_return/sharpe/max_dd): {bt_results.get(name)}")
        print(f"  Backtest signals on latest bar: {'YES' if backtest_flag else 'NO'}")
        if summary.get('signal') == 'BUY':
            print(f"  Live Signal: BUY @ {summary['entry_price']:.0f}, SL {summary['stop_loss']:.0f}, TP {summary['take_profit']:.0f}")
            print(f"    Shares: {summary['shares']}, Invest: Rp{summary['investment']:,.0f}")
            print(f"    Risk: Rp{summary['risk_amount']:,.0f} ({summary['risk_pct']:.2f}%)")
            print(f"    TP potential: {summary['tp_return_pct']:.1f}% | SL potential: {summary['sl_return_pct']:.1f}%")
        else:
            print(f"  Live Signal: {summary.get('signal')}")

        print('-' * 80)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--start', default='2024-01-01')
    parser.add_argument('--cash', type=float, default=1_000_000)
    args = parser.parse_args()

    compare(args.symbol, args.start, args.cash)


if __name__ == '__main__':
    main()
