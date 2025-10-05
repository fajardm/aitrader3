import argparse
import pandas as pd
import numpy as np
from fetch_data import load_ohlcv
from trading_strategies import BacktestStrategy
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
            if strategy_type == "pullback":
                has_signal = BacktestStrategy.has_pullback_signal(row)
            else:  # breakout
                has_signal = BacktestStrategy.has_breakout_signal(row)
            
            if has_signal:
                position_open = True
                entries.iloc[i] = True
                days_held = 0
                
                # Store which level was triggered for exit calculation
                if strategy_type == "pullback":
                    pullback_status = BacktestStrategy.check_pullback_conditions(row)
                    triggered_level = BacktestStrategy.determine_pullback_level(pullback_status)
                    df.loc[df.index[i], 'triggered_level'] = triggered_level
                else:  # breakout
                    breakout_status = BacktestStrategy.check_breakout_conditions(row)
                    triggered_level = BacktestStrategy.determine_breakout_level(breakout_status)
                    df.loc[df.index[i], 'triggered_level'] = triggered_level
            
        elif position_open:
            days_held += 1
            
            # Get entry details
            entry_price = df['close'].iloc[i - days_held]  # Price when entered
            entry_idx = i - days_held
            triggered_level = df.iloc[entry_idx].get('triggered_level', 'R3' if strategy_type == 'breakout' else 'R2')
            
            # Check if position should exit using centralized logic
            should_exit, exit_reason = BacktestStrategy.should_exit_position(
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
    shares, investment = BacktestStrategy.calculate_position_size(available_cash, entry_price, sl_price, risk_pct)
    
    # Apply cash constraint (leave 5% buffer)
    max_investment = available_cash * 0.95
    if investment > max_investment:
        shares = int(max_investment / entry_price)
    return shares


def run_realistic_backtest(df: pd.DataFrame, strategy_name: str, initial_cash: float = 1_000_000):
    """Run backtest with REALISTIC cash management"""
    print(f"\n=== {strategy_name} Strategy (Realistic) ===")
    
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
            if strategy_type == "pullback":
                pullback_status = BacktestStrategy.check_pullback_conditions(row)
                entry_level = BacktestStrategy.determine_pullback_level(pullback_status)
            else:  # breakout
                breakout_status = BacktestStrategy.check_breakout_conditions(row)
                entry_level = BacktestStrategy.determine_breakout_level(breakout_status)
            
            # Get strategy parameters using centralized logic
            if strategy_type == "pullback":
                # For pullback, entry price is the support level
                entry_price = row['R1'] if entry_level == 'R1' else row['R2']
                params = BacktestStrategy.get_pullback_parameters(entry_level, atr, entry_price)
            else:  # breakout
                entry_price = current_price
                params = BacktestStrategy.get_breakout_parameters(entry_level, atr, entry_price)
            
            sl_price = params['stop_loss']
            tp_price = params['take_profit']
            
            # Calculate position size based on CURRENT available cash
            shares = calculate_realistic_position_size(cash, entry_price, sl_price, 0.02)
            investment = shares * entry_price
            risk_amount = shares * abs(entry_price - sl_price)
            risk_pct = risk_amount / cash if cash > 0 else 0
            
            if shares > 0 and investment <= cash:
                # Execute trade
                shares_held = shares
                cash -= investment
                position_open = True
                
                print(f"ENTRY: {date.strftime('%Y-%m-%d')} @ {entry_price:.0f} ({entry_level}), "
                      f"Shares: {shares}, Investment: {investment:,.0f}, "
                      f"Risk: {risk_pct*100:.2f}%, Available Cash: {cash:,.0f}")
        
        elif exits.iloc[i] and position_open:
            # Exit position
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
            
            print(f"EXIT:  {date.strftime('%Y-%m-%d')} @ {exit_price:.0f}, "
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
        avg_return = trades_df['return_pct'].mean()
        
        winning_trades = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        losing_trades = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = winning_trades / losing_trades if losing_trades > 0 else float('inf')
        
        avg_investment = (trades_df['shares'] * trades_df['entry_price']).mean()
        avg_investment_pct = (avg_investment / initial_cash) * 100
        
    else:
        win_rate = 0
        avg_return = 0
        profit_factor = 0
        avg_investment = 0
        avg_investment_pct = 0
    
    print(f"\n=== REALISTIC RESULTS ===")
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', required=True, 
                       help='Stock symbol (e.g., WIFI.JK, BBCA.JK, GOTO.JK)')
    parser.add_argument('--cash', type=float, default=1_000_000, help='Initial cash')
    args = parser.parse_args()
    
    # Load live data
    print(f"Loading live data for: {args.symbol}")
    df = load_ohlcv(args.symbol, "2024-01-01")

    df = calculate_indicators(df)
    
    print(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    print(f"Price range: {df['close'].min():.0f} - {df['close'].max():.0f}")
    print(f"Target: 2% risk per trade = Rp{args.cash * 0.02:,.0f} max risk per trade")
    
    # Test both strategies with REALISTIC cash management
    print("\n" + "="*60)
    pullback_final, pullback_return, pullback_dd, pullback_sharpe = run_realistic_backtest(df, "Pullback", args.cash)
    
    print("\n" + "="*60)
    breakout_final, breakout_return, breakout_dd, breakout_sharpe = run_realistic_backtest(df, "Breakout", args.cash)
    
    # Summary comparison
    print(f"\n" + "="*60)
    print(f"=== FINAL REALISTIC COMPARISON ===")
    print(f"Pullback: {pullback_return:.1f}% return, {pullback_dd:.1f}% DD, {pullback_sharpe:.2f} Sharpe")
    print(f"Breakout: {breakout_return:.1f}% return, {breakout_dd:.1f}% DD, {breakout_sharpe:.2f} Sharpe")
    print(f"="*60)


if __name__ == '__main__':
    main()