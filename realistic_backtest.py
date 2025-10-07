import argparse
import pandas as pd
import numpy as np
from fetch_data import load_ohlcv
from trading_strategies import TradingStrategy
from indicators import calculate_indicators


def generate_realistic_signals(df: pd.DataFrame, strategy_type: str) -> tuple[pd.Series, pd.Series]:
    """Generate signals with realistic position sizing constraints using centralized strategy logic"""
    
    entries = pd.Series(False, index=df.index)
    exits = pd.Series(False, index=df.index)
    
    position_open = False
    days_held = 0
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        if not position_open:
            # Check for entry signal using centralized logic
            if strategy_type.lower() == "resistance_retest":
                has_signal = TradingStrategy.has_resistance_retest_signal(row)
            elif strategy_type.lower() == "pullback":
                has_signal = TradingStrategy.has_pullback_signal(row)
            else:  # breakout
                has_signal = TradingStrategy.has_breakout_signal(row)
            
            if has_signal:
                position_open = True
                entries.iloc[i] = True
                days_held = 0
                
                # Store which level was triggered for exit calculation
                if strategy_type.lower() == "resistance_retest":
                    retest_status = TradingStrategy.check_resistance_retest_conditions(row)
                    triggered_level = TradingStrategy.determine_resistance_retest_level(retest_status)
                elif strategy_type.lower() == "pullback":
                    pullback_status = TradingStrategy.check_pullback_conditions(row)
                    triggered_level = TradingStrategy.determine_pullback_level(pullback_status)
                else:  # breakout
                    breakout_status = TradingStrategy.check_breakout_conditions(row)
                    triggered_level = TradingStrategy.determine_breakout_level(breakout_status)
                
                # Store triggered level for all strategies
                df.loc[df.index[i], 'triggered_level'] = triggered_level
            
        elif position_open:
            days_held += 1
            
            # Get entry details
            entry_price = df['close'].iloc[i - days_held]  # Price when entered
            entry_idx = i - days_held
            triggered_level = df.iloc[entry_idx].get('triggered_level', 'R3' if strategy_type == 'breakout' else 'R2')
            
            # Check if position should exit using local logic
            should_exit, exit_reason = should_exit_position(
                row, entry_price, strategy_type, triggered_level, days_held
            )
            
            if should_exit:
                exits.iloc[i] = True
                position_open = False
                days_held = 0
    
    print(f"Realistic {strategy_type}: {entries.sum()} entries, {exits.sum()} exits")
    return entries, exits


def calculate_realistic_position_size(available_cash: float, entry_price: float, sl_price: float, risk_pct: float = 0.02):
    """Calculate realistic position size with proper cash management - using centralized logic"""
    shares, investment = TradingStrategy.calculate_position_size(available_cash, entry_price, sl_price, risk_pct)
    
    # Apply cash constraint (leave 5% buffer)
    max_investment = available_cash * 0.95
    if investment > max_investment:
        shares = int(max_investment / entry_price)
    return shares


def run_realistic_backtest(df: pd.DataFrame, strategy_name: str, initial_cash: float = 1_000_000):
    """Run backtest with REALISTIC cash management"""
    print("\n=== {} Strategy (Realistic) ===".format(strategy_name))
    
    strategy_type = strategy_name.lower()
    entries, exits = generate_realistic_signals(df, strategy_type)
    
    # Manual portfolio simulation with proper cash tracking
    cash = initial_cash
    shares_held = 0
    portfolio_value = []
    trade_log = []
    
    position_open = False
    entry_price = 0
    entry_date = None
    sl_price = 0
    tp_price = 0
    
    for i, (date, row) in enumerate(df.iterrows()):
        current_price = row['close']
        
        # Calculate current portfolio value
        if shares_held > 0:
            current_value = cash + (shares_held * current_price)
        else:
            current_value = cash
        portfolio_value.append(current_value)
        
        if entries.iloc[i] and not position_open:
            # Enter position using centralized logic
            atr = row['atr14']
            
            # Determine triggered level using centralized logic
            if strategy_type.lower() in ["resistance_retest"]:
                retest_status = TradingStrategy.check_resistance_retest_conditions(row)
                entry_level = TradingStrategy.determine_resistance_retest_level(retest_status)
            elif strategy_type.lower() == "pullback":
                pullback_status = TradingStrategy.check_pullback_conditions(row)
                entry_level = TradingStrategy.determine_pullback_level(pullback_status)
            else:  # breakout
                breakout_status = TradingStrategy.check_breakout_conditions(row)
                entry_level = TradingStrategy.determine_breakout_level(breakout_status)
            
            # Get strategy parameters using centralized logic
            if strategy_type.lower() in ["resistance_retest"]:
                # For resistance retest, entry price is the resistance level
                entry_price = row[f'R{entry_level[-1]}']  # Extract number from 'R1' or 'R2'
                params = TradingStrategy.get_resistance_retest_parameters(entry_level, atr, entry_price)
            elif strategy_type.lower() == "pullback":
                # For pullback, entry price is the support level
                entry_price = row[f'S{entry_level[-1]}']  # Extract number from 'S1', 'S2', or 'S3'
                params = TradingStrategy.get_pullback_parameters(entry_level, atr, entry_price)
            else:  # breakout
                entry_price = current_price
                params = TradingStrategy.get_breakout_parameters(entry_level, atr, entry_price)
            
            sl_price = params['stop_loss']
            tp_price = params['take_profit']
            
            shares = calculate_realistic_position_size(cash, entry_price, sl_price, 0.02)
            investment = shares * entry_price
            risk_amount = shares * abs(entry_price - sl_price)
            risk_pct = risk_amount / cash if cash > 0 else 0
            
            if shares > 0 and investment <= cash:
                # Execute trade
                shares_held = shares
                cash -= investment
                position_open = True
                entry_date = date  # Store entry date
                
                print(f"ENTRY: {date.strftime('%Y-%m-%d')} @ {entry_price:.0f} ({entry_level}), "
                      f"Shares: {shares}, Investment: {investment:,.0f}, "
                      f"Risk: {risk_pct*100:.2f}%, Available Cash: {cash:,.0f}")
        
        elif exits.iloc[i] and position_open:
            # Get exit reason to determine correct exit price
            # Use stored entry parameters, not recalculated ones
            try:
                days_held = i - df.index.get_loc(entry_date) if entry_date else 0
            except (KeyError, ValueError):
                days_held = 0
            
            _, exit_reason = should_exit_position(
                row, entry_price, strategy_type, entry_level, days_held
            )
            
            # Use appropriate exit price based on exit reason
            if exit_reason == 'take_profit':
                exit_price = tp_price  # Use stored take profit from entry
            elif exit_reason == 'stop_loss':
                exit_price = sl_price  # Use stored stop loss from entry
            else:  # time_exit
                exit_price = current_price
            
            proceeds = shares_held * exit_price
            cash += proceeds
            
            # Calculate trade P&L
            trade_pnl = proceeds - (shares_held * entry_price)
            trade_return = (exit_price / entry_price - 1) * 100
            
            trade_log.append({
                'entry_date': entry_date,
                'exit_date': date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'shares': shares_held,
                'pnl': trade_pnl,
                'return_pct': trade_return
            })
            
            print(f"EXIT:  {date.strftime('%Y-%m-%d')} @ {exit_price:.0f} ({exit_reason}), "
                  f"P&L: {trade_pnl:,.0f}, Return: {trade_return:.1f}%, "
                  f"New Cash: {cash:,.0f}")
            
            shares_held = 0
            position_open = False
    
    # Final portfolio value
    final_value = cash + (shares_held * df['close'].iloc[-1])
    total_return = (final_value / initial_cash - 1) * 100
    
    # Calculate performance metrics
    portfolio_values = pd.Series(portfolio_value, index=df.index)
    returns = portfolio_values.pct_change().dropna()
    
    if len(returns) > 0:
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        max_dd = ((portfolio_values / portfolio_values.cummax()) - 1).min() * 100
    else:
        sharpe = 0
        max_dd = 0
    
    # Trade statistics
    if trade_log:
        trades_df = pd.DataFrame(trade_log)
        win_rate = (trades_df['pnl'] > 0).mean() * 100

        winning_trades = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        losing_trades = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = winning_trades / losing_trades if losing_trades > 0 else float('inf')

        avg_investment = (trades_df['shares'] * trades_df['entry_price']).mean()
        avg_investment_pct = (avg_investment / initial_cash) * 100
    else:
        win_rate = 0
        profit_factor = 0
        avg_investment = 0
        avg_investment_pct = 0

    print("\n=== REALISTIC RESULTS ===")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Total Trades: {len(trade_log)}")
    print(f"Final Value: Rp{final_value:,.0f}")
    print(f"Final Cash: Rp{cash:,.0f}")
    print(f"Avg Investment: Rp{avg_investment:,.0f} ({avg_investment_pct:.1f}% of initial capital)")
    print(f"Profit Factor: {profit_factor:.2f}")
    
    return final_value, total_return, max_dd, sharpe


def should_exit_position(row, entry_price: float, strategy_type: str, triggered_level: str, days_held: int):
    """Check if position should be exited - backtest specific logic with intraday execution"""
    
    # Get parameters based on strategy
    atr = row['atr14']  # Fixed: use correct column name
    
    if strategy_type.lower() == "pullback":
        params = TradingStrategy.get_pullback_parameters(triggered_level, atr, entry_price)
    elif strategy_type.lower() == "resistance_retest":
        params = TradingStrategy.get_resistance_retest_parameters(triggered_level, atr, entry_price)
    else:  # breakout
        params = TradingStrategy.get_breakout_parameters(triggered_level, atr, entry_price)
    
    # Check exit conditions using REALISTIC intraday prices
    if row['low'] <= params['stop_loss']:      # Use LOW for stop loss detection
        return True, "stop_loss"
    
    # Check take profit using HIGH (more realistic than close)
    if row['high'] >= params['take_profit']:   # Use HIGH for take profit detection
        return True, "take_profit"
    
    # Check max holding days
    if days_held >= params['max_days']:
        return True, "max_days"
    
    return False, ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g., BBRI.JK)')
    parser.add_argument('--cash', type=float, default=1_000_000, help='Initial cash')
    args = parser.parse_args()
    
    # Load live data
    print(f"Loading live data for: {args.symbol}")
    df = load_ohlcv(args.symbol, "2024-01-01")

    df = calculate_indicators(df)
    
    print(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    print(f"Price range: {df['close'].min():.0f} - {df['close'].max():.0f}")
    print(f"Target: 2% risk per trade = Rp{args.cash * 0.02:,.0f} max risk per trade")
    
    # Test all three strategies with REALISTIC cash management
    print("\n" + "="*60)
    print("=== TESTING PULLBACK STRATEGY (Support-based) ===")
    pullback_final, pullback_return, pullback_dd, pullback_sharpe = run_realistic_backtest(df, "Pullback", args.cash)
    
    print("\n" + "="*60)
    print("=== TESTING RESISTANCE RETEST STRATEGY ===")
    resistance_retest_final, resistance_retest_return, resistance_retest_dd, resistance_retest_sharpe = run_realistic_backtest(df, "Resistance_Retest", args.cash)
    
    print("\n" + "="*60)
    print("=== TESTING BREAKOUT STRATEGY ===")
    breakout_final, breakout_return, breakout_dd, breakout_sharpe = run_realistic_backtest(df, "Breakout", args.cash)
    
    # Summary comparison
    print("\n" + "="*60)
    print("=== FINAL REALISTIC COMPARISON ===")
    print(f"Pullback (Support): {pullback_return:.1f}% return, {pullback_dd:.1f}% DD, {pullback_sharpe:.2f} Sharpe")
    print(f"Resistance Retest: {resistance_retest_return:.1f}% return, {resistance_retest_dd:.1f}% DD, {resistance_retest_sharpe:.2f} Sharpe")
    print(f"Breakout: {breakout_return:.1f}% return, {breakout_dd:.1f}% DD, {breakout_sharpe:.2f} Sharpe")
    print("="*60)


if __name__ == '__main__':
    main()