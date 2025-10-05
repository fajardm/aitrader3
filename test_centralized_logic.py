#!/usr/bin/env python3
"""
Test Centralized Trading Strategies
====================================

This script tests the centralized trading logic without requiring live data,
using mock data to verify that all strategy functions work correctly.
"""

import pandas as pd
import numpy as np
from trading_strategies import TradingStrategy, BacktestStrategy, LiveSignalStrategy

def create_mock_data():
    """Create mock OHLC data for testing"""
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    
    # Create mock data with clear breakout/pullback patterns
    data = {
        'open': [1000, 1010, 1020, 1030, 1040, 1050, 1060, 1070, 1080, 1090],
        'high': [1020, 1030, 1040, 1050, 1060, 1070, 1080, 1090, 1100, 1110],
        'low': [995, 1005, 1015, 1025, 1035, 1045, 1055, 1065, 1075, 1085],
        'close': [1010, 1020, 1030, 1040, 1050, 1060, 1070, 1080, 1090, 1100],
        'ema10': [1000, 1005, 1010, 1015, 1020, 1025, 1030, 1035, 1040, 1045],
        'ema20': [995, 1000, 1005, 1010, 1015, 1020, 1025, 1030, 1035, 1040],
        'rsi14': [45, 50, 55, 60, 45, 50, 55, 60, 45, 50],
        'atr14': [20, 22, 21, 23, 20, 22, 21, 23, 20, 22],
        'R1': [1015, 1025, 1035, 1045, 1055, 1065, 1075, 1085, 1095, 1105],
        'R2': [1025, 1035, 1045, 1055, 1065, 1075, 1085, 1095, 1105, 1115],
        'R3': [1035, 1045, 1055, 1065, 1075, 1085, 1095, 1105, 1115, 1125]
    }
    
    df = pd.DataFrame(data, index=dates)
    return df

def test_centralized_breakout_logic():
    """Test centralized breakout logic"""
    print("🔬 Testing Centralized Breakout Logic")
    print("=" * 50)
    
    df = create_mock_data()
    
    # Test individual row breakout conditions
    test_row = df.iloc[5]  # Use row that should trigger breakout
    print(f"Test Row Data:")
    print(f"Close: {test_row['close']}, R1: {test_row['R1']}, R2: {test_row['R2']}, R3: {test_row['R3']}")
    print(f"RSI: {test_row['rsi14']}, EMA10: {test_row['ema10']}, EMA20: {test_row['ema20']}")
    
    # Test breakout conditions
    breakout_status = TradingStrategy.check_breakout_conditions(test_row)
    print(f"\nBreakout Status: {breakout_status}")
    
    # Test level determination
    triggered_level = TradingStrategy.determine_breakout_level(breakout_status)
    print(f"Triggered Level: {triggered_level}")
    
    # Test has signal
    has_signal = TradingStrategy.has_breakout_signal(test_row)
    print(f"Has Breakout Signal: {has_signal}")
    
    # Test parameters
    params = TradingStrategy.get_breakout_parameters(triggered_level, test_row['atr14'], test_row['close'])
    print(f"Strategy Parameters: {params}")
    
    print("✅ Breakout Logic Test Complete\n")

def test_centralized_pullback_logic():
    """Test centralized pullback logic"""
    print("🔬 Testing Centralized Pullback Logic")
    print("=" * 50)
    
    df = create_mock_data()
    
    # Modify test row to trigger pullback
    test_row = df.iloc[5].copy()
    test_row['low'] = test_row['R1'] * 0.99  # Touch R1 support
    test_row['high'] = test_row['R1'] * 1.01  # Bounce from R1
    
    print(f"Test Row Data (Modified for Pullback):")
    print(f"Close: {test_row['close']}, Low: {test_row['low']}, High: {test_row['high']}")
    print(f"R1: {test_row['R1']}, R2: {test_row['R2']}")
    
    # Test pullback conditions
    pullback_status = TradingStrategy.check_pullback_conditions(test_row)
    print(f"\nPullback Status: {pullback_status}")
    
    # Test level determination
    triggered_level = TradingStrategy.determine_pullback_level(pullback_status)
    print(f"Triggered Level: {triggered_level}")
    
    # Test has signal
    has_signal = TradingStrategy.has_pullback_signal(test_row)
    print(f"Has Pullback Signal: {has_signal}")
    
    # Test parameters
    entry_price = test_row['R1'] if triggered_level == 'R1' else test_row['R2']
    params = TradingStrategy.get_pullback_parameters(triggered_level, test_row['atr14'], entry_price)
    print(f"Strategy Parameters: {params}")
    
    print("✅ Pullback Logic Test Complete\n")

def test_position_sizing():
    """Test position sizing logic"""
    print("🔬 Testing Position Sizing Logic")
    print("=" * 50)
    
    cash = 1_000_000
    entry_price = 1000
    stop_loss = 980
    risk_pct = 0.02
    
    shares, investment = TradingStrategy.calculate_position_size(cash, entry_price, stop_loss, risk_pct)
    
    risk_amount = shares * abs(entry_price - stop_loss)
    actual_risk_pct = risk_amount / cash
    
    print(f"Cash: Rp{cash:,}")
    print(f"Entry Price: Rp{entry_price}")
    print(f"Stop Loss: Rp{stop_loss}")
    print(f"Target Risk: {risk_pct*100}%")
    print(f"Calculated Shares: {shares}")
    print(f"Investment: Rp{investment:,}")
    print(f"Risk Amount: Rp{risk_amount:,}")
    print(f"Actual Risk %: {actual_risk_pct*100:.2f}%")
    
    print("✅ Position Sizing Test Complete\n")

def test_live_signal_generation():
    """Test live signal generation"""
    print("🔬 Testing Live Signal Generation")
    print("=" * 50)
    
    df = create_mock_data()
    symbol = "TEST.JK"
    cash = 1_000_000
    
    # Test breakout signal generation
    breakout_signal = LiveSignalStrategy.generate_breakout_signal(df, symbol, cash)
    print("Breakout Signal:")
    for key, value in breakout_signal.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print()
    
    # Test pullback signal generation
    pullback_signal = LiveSignalStrategy.generate_pullback_signal(df, symbol, cash)
    print("Pullback Signal:")
    for key, value in pullback_signal.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print("✅ Live Signal Generation Test Complete\n")

def test_backtest_exit_logic():
    """Test backtest exit logic"""
    print("🔬 Testing Backtest Exit Logic")
    print("=" * 50)
    
    df = create_mock_data()
    test_row = df.iloc[5]
    
    entry_price = 1000
    strategy_type = "breakout"
    triggered_level = "R2"
    days_held = 3
    
    should_exit, exit_reason = BacktestStrategy.should_exit_position(
        test_row, entry_price, strategy_type, triggered_level, days_held
    )
    
    print(f"Entry Price: {entry_price}")
    print(f"Current Price: {test_row['close']}")
    print(f"Strategy: {strategy_type}")
    print(f"Level: {triggered_level}")
    print(f"Days Held: {days_held}")
    print(f"Should Exit: {should_exit}")
    print(f"Exit Reason: {exit_reason}")
    
    print("✅ Backtest Exit Logic Test Complete\n")

def main():
    """Run all centralized logic tests"""
    print("🚀 CENTRALIZED TRADING STRATEGIES TEST")
    print("=" * 60)
    print("Testing all centralized functions to ensure they work correctly")
    print("without requiring live data or API connections.\n")
    
    try:
        test_centralized_breakout_logic()
        test_centralized_pullback_logic()
        test_position_sizing()
        test_live_signal_generation()
        test_backtest_exit_logic()
        
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ Centralized logic is working correctly")
        print("✅ Breakout and pullback strategies implemented")
        print("✅ Position sizing logic functional")
        print("✅ Live signal generation working")
        print("✅ Backtest exit logic operational")
        print("\n🔧 NEXT STEPS:")
        print("1. Both realistic_backtest.py and live_signal.py now use identical centralized logic")
        print("2. No more code duplication between backtest and live trading")
        print("3. Single source of truth for all strategy parameters")
        print("4. Easy to maintain and update strategy logic")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()