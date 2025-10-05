#!/usr/bin/env python3
"""
Indonesian Stock Live Signal Generator
Based on proven breakout/pullback strategies with 2% risk management
Supports any Indonesian stock symbol (*.JK format)
"""

import pandas as pd
import argparse
from fetch_data import load_ohlcv
from trading_strategies import LiveSignalStrategy
from indicators import calculate_indicators

def check_breakout_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> dict:
    """Check for breakout entry signal using centralized strategy logic"""
    return LiveSignalStrategy.generate_breakout_signal(df, symbol, cash)


def check_pullback_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> dict:
    """Check for pullback entry signal using centralized strategy logic"""
    return LiveSignalStrategy.generate_pullback_signal(df, symbol, cash)


def display_signal(signal: dict):
    """Display signal in formatted output"""
    print(f"\n{'='*60}")
    print(f"🎯 {signal['symbol']} LIVE SIGNAL - {signal['date']}")
    print(f"{'='*60}")
    print(f"Strategy: {signal['strategy']}")
    print(f"Signal: {signal['signal']}")
    print(f"Current Price: Rp {signal['current_price']:,.0f}")
    
    if signal['strategy'] == 'BREAKOUT':
        print(f"R1 Level: Rp {signal['r1_level']:,.0f}")
        print(f"R2 Level: Rp {signal['r2_level']:,.0f}")
        print(f"R3 Level: Rp {signal['r3_level']:,.0f}")
        
        # Show breakout status for each level
        r1_status = "✅ ABOVE R1" if signal['current_price'] > signal['r1_level'] else "❌ BELOW R1"
        r2_status = "✅ ABOVE R2" if signal['current_price'] > signal['r2_level'] else "❌ BELOW R2"
        r3_status = "✅ ABOVE R3" if signal['current_price'] > signal['r3_level'] else "❌ BELOW R3"
        
        print(f"Breakout Status:")
        print(f"  {r1_status}")
        print(f"  {r2_status}")
        print(f"  {r3_status}")
        
        # Show which level is closest for potential breakout
        r1_distance = abs(signal['current_price'] - signal['r1_level'])
        r2_distance = abs(signal['current_price'] - signal['r2_level'])
        r3_distance = abs(signal['current_price'] - signal['r3_level'])
        
        min_distance = min(r1_distance, r2_distance, r3_distance)
        if min_distance == r1_distance:
            closest_level = "R1"
        elif min_distance == r2_distance:
            closest_level = "R2"
        else:
            closest_level = "R3"
        print(f"Closest Level: {closest_level} (distance: Rp {min_distance:,.0f})")
    else:  # PULLBACK
        print(f"R1 Level: Rp {signal['r1_level']:,.0f}")
        print(f"R2 Level: Rp {signal['r2_level']:,.0f}")
        print(f"EMA20: Rp {signal['ema20']:,.0f}")
        above_ema = "✅ ABOVE EMA20" if signal['current_price'] > signal['ema20'] else "❌ BELOW EMA20"
        print(f"Trend Status: {above_ema}")
        
        # Show which level is closer for potential pullback
        r1_distance = abs(signal['current_price'] - signal['r1_level'])
        r2_distance = abs(signal['current_price'] - signal['r2_level'])
        closer_level = "R1" if r1_distance < r2_distance else "R2"
        print(f"Closer Level: {closer_level} (distance: Rp {min(r1_distance, r2_distance):,.0f})")
    
    print(f"RSI(14): {signal['rsi14']:.1f}")
    print(f"ATR(14): Rp {signal['atr14']:,.0f}")
    
    if signal['signal'] == 'BUY':
        print(f"\n🚀 BUY SIGNAL DETECTED!")
        
        # Add timing guidance
        if signal['strategy'] == 'BREAKOUT':
            entry_level_name = signal.get('entry_level', 'R3')
            print(f"⏰ TIMING: Execute immediately if during market hours")
            print(f"📍 ACTION: {entry_level_name} breakout confirmed - buy at current price")
            
            # Add specific guidance based on breakout level
            if entry_level_name == 'R1':
                print(f"💡 STRATEGY: Early momentum entry - watch for quick moves")
            elif entry_level_name == 'R2':
                print(f"💡 STRATEGY: Confirmed breakout - balanced risk/reward")
            else:  # R3
                print(f"💡 STRATEGY: Strong momentum - high confidence trade")
        else:  # PULLBACK
            entry_level_name = signal.get('entry_level', 'R2')
            print(f"⏰ TIMING: Wait for price to reach {entry_level_name} level")
            print(f"📍 ACTION: Set limit order at {entry_level_name} or watch for pullback to support")
            
        print(f"Entry Price: Rp {signal['entry_price']:,.0f}")
        print(f"Stop Loss: Rp {signal['stop_loss']:,.0f} (-{((signal['entry_price'] - signal['stop_loss'])/signal['entry_price']*100):.1f}%)")
        print(f"Take Profit: Rp {signal['take_profit']:,.0f} (+{((signal['take_profit'] - signal['entry_price'])/signal['entry_price']*100):.1f}%)")
        print(f"Recommended Shares: {signal['shares']:,}")
        print(f"Investment Amount: Rp {signal['investment']:,.0f}")
        print(f"Risk Amount: Rp {signal['risk_amount']:,.0f} ({signal['risk_percent']:.2f}%)")
        print(f"Max Hold Period: {signal['max_hold_days']} days")
        
        print(f"\n📋 TRADING PLAN:")
        print(f"1. Buy {signal['shares']:,} shares at Rp {signal['entry_price']:,.0f}")
        print(f"2. Set stop loss at Rp {signal['stop_loss']:,.0f}")
        print(f"3. Set take profit at Rp {signal['take_profit']:,.0f}")
        print(f"4. Exit if no movement after {signal['max_hold_days']} days")
    else:
        print(f"\n⏳ NO SIGNAL - Wait for better entry")
    
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Live Signal Generator for Indonesian Stocks')
    parser.add_argument('--symbol', type=str, default='WIFI.JK', 
                       help='Stock symbol (default: WIFI.JK). Examples: BBCA.JK, GOTO.JK, TLKM.JK')
    parser.add_argument('--cash', type=float, default=1_000_000, help='Available cash (default: 1,000,000)')
    parser.add_argument('--strategy', choices=['breakout', 'pullback', 'both'], default='both', 
                       help='Strategy to check (default: both)')
    args = parser.parse_args()
    
    try:
        # Fetch latest data
        df = load_ohlcv(args.symbol, "2023-01-01")
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Check signals
        if args.strategy in ['breakout', 'both']:
            breakout_signal = check_breakout_signal(df, args.symbol, args.cash)
            display_signal(breakout_signal)
        
        if args.strategy in ['pullback', 'both']:
            pullback_signal = check_pullback_signal(df, args.symbol, args.cash)
            display_signal(pullback_signal)
        
        # Show recent price action
        recent = df.tail(5)[['close', 'R1', 'R2', 'R3', 'rsi14', 'atr14']].round(0)
        print(f"\n📊 RECENT PRICE ACTION (Last 5 days):")
        print(recent.to_string())
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have internet connection and the investiny package installed")
        print("Install investiny with: pip install git+https://github.com/fajardm/investiny.git")
        print("Valid Indonesian stock symbols should end with .JK (e.g., BBCA.JK)")


if __name__ == '__main__':
    main()