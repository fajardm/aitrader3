#!/usr/bin/env python3
"""
Indonesian Stock Live Signal Generator
Based on proven breakout/pullback strategies with 2% risk management
Supports any Indonesian stock symbol (*.JK format)
"""

import pandas as pd
import numpy as np
import ta
from datetime import datetime
import argparse
from fetch_data import load_ohlcv


def fetch_latest_data(symbol: str = "WIFI.JK", start_date: str = "2023-01-01") -> pd.DataFrame:
    """Fetch latest data from investiny (Indonesian stock data source)"""
    print(f"Fetching latest data for {symbol}...")
    
    try:
        # Use investiny for Indonesian stock data
        print("Using investiny data source...")
        df = load_ohlcv(symbol, start=start_date)
        
        # Convert to expected format
        df.index.name = 'date'
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        print(f"Downloaded {len(df)} bars from {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
        return df
        
    except Exception as e:
        raise Exception(f"Failed to fetch data for {symbol}: {e}")


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators"""
    # EMAs
    df['ema5'] = ta.trend.ema_indicator(df['close'], window=5)
    df['ema10'] = ta.trend.ema_indicator(df['close'], window=10)
    df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['ema100'] = ta.trend.ema_indicator(df['close'], window=100)
    df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
    
    # RSI and ATR
    df['rsi14'] = ta.momentum.rsi(df['close'], window=14)
    df['atr14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    
    # Classic Pivot Points (using previous day's data)
    df['P'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['R1'] = 2 * df['P'] - df['low'].shift(1)
    df['R2'] = df['P'] + (df['high'].shift(1) - df['low'].shift(1))
    df['R3'] = df['high'].shift(1) + 2 * (df['P'] - df['low'].shift(1))
    df['S1'] = 2 * df['P'] - df['high'].shift(1)
    df['S2'] = df['P'] - (df['high'].shift(1) - df['low'].shift(1))
    df['S3'] = df['low'].shift(1) - 2 * (df['high'].shift(1) - df['P'])
    
    return df


def calculate_position_size(available_cash: float, entry_price: float, sl_price: float, risk_pct: float = 0.02):
    """Calculate position size with 2% risk management"""
    max_risk = available_cash * risk_pct
    risk_per_share = abs(entry_price - sl_price)
    
    if risk_per_share <= 0:
        return 0, 0
    
    shares_by_risk = int(max_risk / risk_per_share)
    max_investment = available_cash * 0.95  # 5% cash buffer
    shares_by_cash = int(max_investment / entry_price)
    
    final_shares = min(shares_by_risk, shares_by_cash)
    actual_investment = final_shares * entry_price
    
    return final_shares, actual_investment


def check_breakout_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> dict:
    """Check for breakout entry signal (multi-level R1/R2/R3 strategy)"""
    latest = df.iloc[-1]
    
    # Multi-level breakout conditions (same as improved backtest)
    r1_breakout = (latest['close'] > latest['R1']) and (latest['rsi14'] > 35) and (latest['close'] > latest['ema10'])
    r2_breakout = (latest['close'] > latest['R2']) and (latest['rsi14'] > 40) and (latest['close'] > latest['ema20'])
    r3_breakout = (latest['close'] > latest['R3']) and (latest['rsi14'] > 40)
    
    breakout_signal = (r1_breakout or r2_breakout or r3_breakout) and pd.notna(latest['R1']) and pd.notna(latest['R2']) and pd.notna(latest['R3']) and pd.notna(latest['atr14'])
    
    signal_data = {
        'date': latest.name.strftime('%Y-%m-%d'),
        'symbol': symbol,
        'strategy': 'BREAKOUT',
        'signal': 'BUY' if breakout_signal else 'HOLD',
        'current_price': latest['close'],
        'r1_level': latest['R1'],
        'r2_level': latest['R2'],
        'r3_level': latest['R3'],
        'rsi14': latest['rsi14'],
        'atr14': latest['atr14']
    }
    
    if breakout_signal:
        # Determine which level was broken (priority: R3 > R2 > R1)
        if r3_breakout:
            # R3 breakout - strong momentum
            entry_level = "R3"
            sl_price = latest['close'] - 1.2 * latest['atr14']
            tp_price = latest['close'] + 2.5 * latest['atr14']
            max_hold_days = 8
        elif r2_breakout:
            # R2 breakout - confirmed momentum
            entry_level = "R2"
            sl_price = latest['close'] - 1.0 * latest['atr14']
            tp_price = latest['close'] + 2.0 * latest['atr14']
            max_hold_days = 6
        else:
            # R1 breakout - early momentum
            entry_level = "R1"
            sl_price = latest['close'] - 0.8 * latest['atr14']
            tp_price = latest['close'] + 1.5 * latest['atr14']
            max_hold_days = 4
        
        # Calculate position size
        shares, investment = calculate_position_size(cash, latest['close'], sl_price, 0.02)
        
        risk_amount = shares * (latest['close'] - sl_price)
        risk_pct = (risk_amount / cash) * 100
        
        signal_data.update({
            'entry_price': latest['close'],
            'entry_level': entry_level,
            'stop_loss': sl_price,
            'take_profit': tp_price,
            'shares': shares,
            'investment': investment,
            'risk_amount': risk_amount,
            'risk_percent': risk_pct,
            'max_hold_days': max_hold_days
        })
    
    return signal_data


def check_pullback_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> dict:
    """Check for pullback entry signal (alternative strategy)"""
    latest = df.iloc[-1]
    
    # Pullback conditions (improved with R1 and R2 levels)
    pullback_signal = (
        # Option 1: Pullback to R1 (closer resistance, more frequent signals)
        ((latest['low'] <= latest['R1'] * 1.01) and 
         (latest['high'] >= latest['R1'] * 0.99) and
         (latest['close'] > latest['R1']) and
         (latest['close'] > latest['ema20'])) or
        # Option 2: Pullback to R2 (stronger support, less frequent but more reliable)
        ((latest['low'] <= latest['R2'] * 1.02) and
         (latest['high'] >= latest['R2'] * 0.98) and
         (latest['close'] > latest['ema20']))
    ) and (latest['rsi14'] < 70) and pd.notna(latest['R1']) and pd.notna(latest['R2']) and pd.notna(latest['atr14'])
    
    signal_data = {
        'date': latest.name.strftime('%Y-%m-%d'),
        'symbol': symbol,
        'strategy': 'PULLBACK',
        'signal': 'BUY' if pullback_signal else 'HOLD',
        'current_price': latest['close'],
        'r1_level': latest['R1'],
        'r2_level': latest['R2'],
        'ema20': latest['ema20'],
        'rsi14': latest['rsi14'],
        'atr14': latest['atr14']
    }
    
    if pullback_signal:
        # Determine which level triggered the signal
        r1_triggered = (latest['low'] <= latest['R1'] * 1.01) and (latest['high'] >= latest['R1'] * 0.99) and (latest['close'] > latest['R1'])
        r2_triggered = (latest['low'] <= latest['R2'] * 1.02) and (latest['high'] >= latest['R2'] * 0.98)
        
        # Calculate SL/TP levels based on triggered level
        if r1_triggered and not r2_triggered:
            # R1 pullback - closer entry, tighter stops
            entry_price = latest['R1']
            sl_price = entry_price - 1.0 * latest['atr14']  # 1 ATR stop loss
            tp_price = entry_price + 2.0 * latest['atr14']  # 2 ATR take profit
            entry_level = "R1"
        else:
            # R2 pullback - stronger support, wider stops
            entry_price = latest['R2']
            sl_price = entry_price - 1.5 * latest['atr14']  # 1.5 ATR stop loss
            tp_price = entry_price + 2.5 * latest['atr14']  # 2.5 ATR take profit
            entry_level = "R2"
        
        # Calculate position size
        shares, investment = calculate_position_size(cash, entry_price, sl_price, 0.02)
        
        risk_amount = shares * (entry_price - sl_price)
        risk_pct = (risk_amount / cash) * 100
        
        signal_data.update({
            'entry_price': entry_price,
            'entry_level': entry_level,
            'stop_loss': sl_price,
            'take_profit': tp_price,
            'shares': shares,
            'investment': investment,
            'risk_amount': risk_amount,
            'risk_percent': risk_pct,
            'max_hold_days': 8
        })
    
    return signal_data


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
        df = fetch_latest_data(args.symbol, "2023-01-01")
        
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