import argparse
import pandas as pd
import numpy as np
import vectorbt as vbt
import ta
from fetch_data import load_ohlcv


def load_data(symbol: str) -> pd.DataFrame:
    """Load OHLCV data from live source and compute indicators"""
    # Load live data using investiny
    df = load_ohlcv(symbol, start='2023-01-01')
    # Convert index to match expected format
    df.index.name = 'date'
    # Rename columns to lowercase
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    # Compute indicators
    df['ema5'] = ta.trend.ema_indicator(df['close'], window=5)
    df['ema10'] = ta.trend.ema_indicator(df['close'], window=10)
    df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['ema100'] = ta.trend.ema_indicator(df['close'], window=100)
    df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
    df['rsi14'] = ta.momentum.rsi(df['close'], window=14)
    df['atr14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    
    # Compute classic pivots
    df['P'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['R1'] = 2 * df['P'] - df['low'].shift(1)
    df['R2'] = df['P'] + (df['high'].shift(1) - df['low'].shift(1))
    df['R3'] = df['high'].shift(1) + 2 * (df['P'] - df['low'].shift(1))
    df['S1'] = 2 * df['P'] - df['high'].shift(1)
    df['S2'] = df['P'] - (df['high'].shift(1) - df['low'].shift(1))
    df['S3'] = df['low'].shift(1) - 2 * (df['high'].shift(1) - df['P'])
    
    return df


def generate_realistic_signals(df: pd.DataFrame, strategy_type: str) -> tuple[pd.Series, pd.Series]:
    """Generate signals with realistic position sizing constraints"""
    
    if strategy_type == "pullback":
        # IMPROVED: Use both R1 and R2 levels (same as live_signal.py)
        entry_condition = (
            # Option 1: Pullback to R1 (closer resistance, more frequent signals)
            (((df['low'] <= df['R1'] * 1.01) & 
              (df['high'] >= df['R1'] * 0.99) &
              (df['close'] > df['R1']) &
              (df['close'] > df['ema20'])) |
             # Option 2: Pullback to R2 (stronger support, less frequent but more reliable)
             ((df['low'] <= df['R2'] * 1.02) &
              (df['high'] >= df['R2'] * 0.98) &
              (df['close'] > df['ema20']))) &
            (df['rsi14'] < 70) &                 # Normal overbought
            df['R1'].notna() &
            df['R2'].notna() &
            df['atr14'].notna()
        )
    else:  # breakout
        # IMPROVED: Use R1, R2, and R3 breakouts (progressive strength)
        entry_condition = (
            # Option 1: R1 breakout (early momentum, more frequent but riskier)
            (((df['close'] > df['R1']) &
              (df['rsi14'] > 35) &
              (df['close'] > df['ema10'])) |
             # Option 2: R2 breakout (confirmed momentum, balanced risk/reward)
             ((df['close'] > df['R2']) &
              (df['rsi14'] > 40) &
              (df['close'] > df['ema20'])) |
             # Option 3: R3 breakout (strong momentum, less frequent but more reliable)
             ((df['close'] > df['R3']) &
              (df['rsi14'] > 40))) &
            df['R1'].notna() &
            df['R2'].notna() &
            df['R3'].notna() &
            df['atr14'].notna()
        )
    
    entries = pd.Series(False, index=df.index)
    exits = pd.Series(False, index=df.index)
    
    position_open = False
    days_held = 0
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        if not position_open and entry_condition.iloc[i]:
            position_open = True
            entries.iloc[i] = True
            days_held = 0
            
            # Store which level was triggered for pullback strategy
            if strategy_type == "pullback":
                # Check which level triggered the signal (same logic as live_signal.py)
                r1_triggered = (row['low'] <= row['R1'] * 1.01) and (row['high'] >= row['R1'] * 0.99) and (row['close'] > row['R1'])
                r2_triggered = (row['low'] <= row['R2'] * 1.02) and (row['high'] >= row['R2'] * 0.98)
                
                # Store triggered level info for exit calculation
                if r1_triggered and not r2_triggered:
                    df.loc[df.index[i], 'triggered_level'] = 'R1'
                else:
                    df.loc[df.index[i], 'triggered_level'] = 'R2'
            else:  # breakout
                # Check which resistance level was broken
                r1_breakout = (row['close'] > row['R1']) and (row['rsi14'] > 35) and (row['close'] > row['ema10'])
                r2_breakout = (row['close'] > row['R2']) and (row['rsi14'] > 40) and (row['close'] > row['ema20']) 
                r3_breakout = (row['close'] > row['R3']) and (row['rsi14'] > 40)
                
                # Priority: R3 > R2 > R1 (stronger breakout preferred)
                if r3_breakout:
                    df.loc[df.index[i], 'triggered_level'] = 'R3'
                elif r2_breakout:
                    df.loc[df.index[i], 'triggered_level'] = 'R2'
                else:
                    df.loc[df.index[i], 'triggered_level'] = 'R1'
            
        elif position_open:
            days_held += 1
            
            # Calculate SL/TP for current position
            entry_price = df['close'].iloc[i - days_held]  # Price when entered
            atr = row['atr14']
            
            if strategy_type == "pullback":
                # Get the triggered level from entry
                entry_idx = i - days_held
                triggered_level = df.iloc[entry_idx].get('triggered_level', 'R2')
                
                if triggered_level == 'R1':
                    # R1 pullback - closer entry, tighter stops
                    sl_price = entry_price - 1.0 * atr
                    tp_price = entry_price + 2.0 * atr
                    max_days = 6
                else:
                    # R2 pullback - stronger support, wider stops
                    sl_price = entry_price - 1.5 * atr
                    tp_price = entry_price + 2.5 * atr
                    max_days = 8
            else:  # breakout
                # Get the triggered level from entry
                entry_idx = i - days_held
                triggered_level = df.iloc[entry_idx].get('triggered_level', 'R3')
                
                if triggered_level == 'R1':
                    # R1 breakout - early momentum, tighter management
                    sl_price = entry_price - 0.8 * atr
                    tp_price = entry_price + 1.5 * atr
                    max_days = 4
                elif triggered_level == 'R2':
                    # R2 breakout - confirmed momentum, balanced approach
                    sl_price = entry_price - 1.0 * atr
                    tp_price = entry_price + 2.0 * atr
                    max_days = 6
                else:  # R3
                    # R3 breakout - strong momentum, wider stops
                    sl_price = entry_price - 1.2 * atr
                    tp_price = entry_price + 2.5 * atr
                    max_days = 8
            
            exit_triggered = False
            
            # Stop Loss hit
            if row['low'] <= sl_price:
                exits.iloc[i] = True
                exit_triggered = True
                
            # Take Profit hit
            elif row['high'] >= tp_price:
                exits.iloc[i] = True
                exit_triggered = True
                
            # Time-based exit
            elif days_held >= max_days:
                exits.iloc[i] = True
                exit_triggered = True
            
            if exit_triggered:
                position_open = False
                days_held = 0
    
    print(f"Realistic {strategy_type}: {entries.sum()} entries, {exits.sum()} exits")
    return entries, exits


def calculate_realistic_position_size(available_cash: float, entry_price: float, sl_price: float, risk_pct: float = 0.02):
    """Calculate realistic position size with proper cash management"""
    
    # Max risk amount = 2% of CURRENT available cash
    max_risk = available_cash * risk_pct
    
    # Risk per share
    risk_per_share = abs(entry_price - sl_price)
    
    if risk_per_share <= 0:
        return 0
    
    # Calculate shares based on risk
    shares_by_risk = int(max_risk / risk_per_share)
    
    # Calculate max shares we can afford with available cash
    # Leave 5% cash buffer
    max_investment = available_cash * 0.95
    shares_by_cash = int(max_investment / entry_price)
    
    # Take the minimum to ensure we don't exceed cash or risk limits
    final_shares = min(shares_by_risk, shares_by_cash)
    
    # Validate
    actual_investment = final_shares * entry_price
    actual_risk = final_shares * risk_per_share
    actual_risk_pct = actual_risk / available_cash if available_cash > 0 else 0
    
    return final_shares, actual_investment, actual_risk, actual_risk_pct


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
            # Enter position
            atr = row['atr14']
            
            if strategy_type == "pullback":
                # Determine which level triggered (same logic as generate_realistic_signals)
                r1_triggered = (row['low'] <= row['R1'] * 1.01) and (row['high'] >= row['R1'] * 0.99) and (row['close'] > row['R1'])
                r2_triggered = (row['low'] <= row['R2'] * 1.02) and (row['high'] >= row['R2'] * 0.98)
                
                if r1_triggered and not r2_triggered:
                    # R1 pullback
                    entry_level = "R1"
                    sl_price = current_price - 1.0 * atr
                    tp_price = current_price + 2.0 * atr
                else:
                    # R2 pullback
                    entry_level = "R2"
                    sl_price = current_price - 1.5 * atr
                    tp_price = current_price + 2.5 * atr
            else:  # breakout
                # Determine which resistance level was broken (priority: R3 > R2 > R1)
                r1_breakout = (row['close'] > row['R1']) and (row['rsi14'] > 35) and (row['close'] > row['ema10'])
                r2_breakout = (row['close'] > row['R2']) and (row['rsi14'] > 40) and (row['close'] > row['ema20'])
                r3_breakout = (row['close'] > row['R3']) and (row['rsi14'] > 40)
                
                if r3_breakout:
                    # R3 breakout - strong momentum
                    entry_level = "R3"
                    sl_price = current_price - 1.2 * atr
                    tp_price = current_price + 2.5 * atr
                elif r2_breakout:
                    # R2 breakout - confirmed momentum  
                    entry_level = "R2"
                    sl_price = current_price - 1.0 * atr
                    tp_price = current_price + 2.0 * atr
                else:
                    # R1 breakout - early momentum
                    entry_level = "R1"
                    sl_price = current_price - 0.8 * atr
                    tp_price = current_price + 1.5 * atr
            
            # Calculate position size based on CURRENT available cash
            shares, investment, risk_amount, risk_pct = calculate_realistic_position_size(
                cash, current_price, sl_price, 0.02
            )
            
            if shares > 0 and investment <= cash:
                # Execute trade
                shares_held = shares
                cash -= investment
                entry_price = current_price
                entry_date = date
                position_open = True
                
                print(f"ENTRY: {date.strftime('%Y-%m-%d')} @ {current_price:.0f} ({entry_level}), "
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
    df = load_data(args.symbol)
    
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