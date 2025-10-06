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


def check_resistance_retest_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> dict:
    """Check for resistance retest entry signal using centralized strategy logic"""
    return LiveSignalStrategy.generate_resistance_retest_signal(df, symbol, cash)


def check_pullback_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> dict:
    """Check for pullback entry signal using centralized strategy logic (support-based)"""
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
        # Enhanced trend analysis for breakout
        rsi = signal['rsi14']
        
        # Comprehensive trend status
        trend_signals = []
        
        # Check resistance breakthrough momentum
        resistance_breakthrough = 0
        if signal['current_price'] > signal['r1_level']:
            resistance_breakthrough += 1
        if signal['current_price'] > signal['r2_level']:
            resistance_breakthrough += 1
        if signal['current_price'] > signal['r3_level']:
            resistance_breakthrough += 1
            
        if resistance_breakthrough >= 2:
            trend_signals.append("BREAK+")
        elif resistance_breakthrough == 1:
            trend_signals.append("BREAK~")
        else:
            trend_signals.append("BREAK-")
            
        if rsi > 50:
            trend_signals.append("RSI+")
        else:
            trend_signals.append("RSI-")
            
        # Volume analysis (if available in signal)
        if 'volume_avg' in signal and signal.get('volume_ratio', 1) > 1.5:
            trend_signals.append("VOL+")
        elif 'volume_avg' in signal and signal.get('volume_ratio', 1) < 0.8:
            trend_signals.append("VOL-")
        else:
            trend_signals.append("VOL~")
        
        # Determine overall trend
        strong_bullish = sum(1 for s in trend_signals if s.endswith("+"))
        neutral = sum(1 for s in trend_signals if s.endswith("~"))
        
        if strong_bullish >= 2:
            trend_status = "🟢 STRONG BREAKOUT MOMENTUM"
        elif strong_bullish == 1 and neutral >= 1:
            trend_status = "🟡 MODERATE MOMENTUM"
        elif strong_bullish == 1:
            trend_status = "🟠 WEAK MOMENTUM"
        else:
            trend_status = "🔴 NO MOMENTUM"
            
        print(f"Overall Trend: {trend_status} ({'/'.join(trend_signals)})")
        
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
    elif signal['strategy'] == 'RESISTANCE_RETEST':
        # Get additional trend indicators
        rsi = signal['rsi14']
        
        # Comprehensive trend status
        trend_signals = []
        if signal['current_price'] > signal['ema20']:
            trend_signals.append("EMA20+")
        else:
            trend_signals.append("EMA20-")
            
        if rsi > 50:
            trend_signals.append("RSI+")
        else:
            trend_signals.append("RSI-")
            
        # Check resistance level position (above R1 is bullish structure)
        resistance_strength = 0
        if signal['current_price'] > signal['r1_level']:
            resistance_strength += 1
        if signal['current_price'] > signal['r2_level']:
            resistance_strength += 1
            
        if resistance_strength >= 1:
            trend_signals.append("RES+")
        else:
            trend_signals.append("RES-")
        
        # Determine overall trend
        bullish_count = sum(1 for signal_item in trend_signals if signal_item.endswith("+"))
        if bullish_count >= 3:
            trend_status = "🟢 STRONG BULLISH"
        elif bullish_count == 2:
            trend_status = "🟡 BULLISH"
        elif bullish_count == 1:
            trend_status = "🟠 MIXED/NEUTRAL"
        else:
            trend_status = "🔴 BEARISH"
            
        print(f"Overall Trend: {trend_status} ({'/'.join(trend_signals)})")
        
        # Show which level is closer for potential resistance retest
        r1_distance = abs(signal['current_price'] - signal['r1_level'])
        r2_distance = abs(signal['current_price'] - signal['r2_level'])
        closer_level = "R1" if r1_distance < r2_distance else "R2"
        print(f"Closer Level: {closer_level} (distance: Rp {min(r1_distance, r2_distance):,.0f})")
    else:  # PULLBACK
        # Get additional trend indicators from signal data
        rsi = signal['rsi14']
        
        # Comprehensive trend status
        trend_signals = []
        if signal['current_price'] > signal['ema20']:
            trend_signals.append("EMA20+")
        else:
            trend_signals.append("EMA20-")
            
        if rsi > 50:
            trend_signals.append("RSI+")
        else:
            trend_signals.append("RSI-")
            
        # Check if price is above multiple support levels (bullish structure)
        support_strength = 0
        if signal['current_price'] > signal['s1_level']:
            support_strength += 1
        if signal['current_price'] > signal['s2_level']:
            support_strength += 1
        if signal['current_price'] > signal['s3_level']:
            support_strength += 1
            
        if support_strength >= 2:
            trend_signals.append("SUP+")
        else:
            trend_signals.append("SUP-")
        
        # Determine overall trend
        bullish_count = sum(1 for signal_item in trend_signals if signal_item.endswith("+"))
        if bullish_count >= 3:
            trend_status = "🟢 STRONG BULLISH"
        elif bullish_count == 2:
            trend_status = "🟡 BULLISH"
        elif bullish_count == 1:
            trend_status = "🟠 MIXED/NEUTRAL"
        else:
            trend_status = "🔴 BEARISH"
            
        print(f"Overall Trend: {trend_status} ({'/'.join(trend_signals)})")
        
        # Show which support level is closest for potential pullback
        s1_distance = abs(signal['current_price'] - signal['s1_level'])
        s2_distance = abs(signal['current_price'] - signal['s2_level'])
        s3_distance = abs(signal['current_price'] - signal['s3_level'])
        
        min_distance = min(s1_distance, s2_distance, s3_distance)
        if min_distance == s1_distance:
            closest_level = "S1"
        elif min_distance == s2_distance:
            closest_level = "S2"
        else:
            closest_level = "S3"
        print(f"Closest Support: {closest_level} (distance: Rp {min_distance:,.0f})")
    
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
        elif signal['strategy'] == 'RESISTANCE_RETEST':
            entry_level_name = signal.get('entry_level', 'R2')
            print(f"⏰ TIMING: Wait for price to reach {entry_level_name} level")
            print(f"📍 ACTION: Set limit order at {entry_level_name} or watch for retest to resistance")
        else:  # PULLBACK
            entry_level_name = signal.get('entry_level', 'S2')
            print(f"⏰ TIMING: Wait for pullback to {entry_level_name} support level")
            print(f"📍 ACTION: Set limit order at {entry_level_name} or watch for bounce from support")
        
        print(f"\n📋 TRADING PLAN:")
        print(f"Entry Price: Rp {signal['entry_price']:,.0f}")
        print(f"Stop Loss: Rp {signal['stop_loss']:,.0f} (-{((signal['entry_price'] - signal['stop_loss'])/signal['entry_price']*100):.1f}%)")
        print(f"Take Profit: Rp {signal['take_profit']:,.0f} (+{((signal['take_profit'] - signal['entry_price'])/signal['entry_price']*100):.1f}%)")
        print(f"Recommended Shares: {signal['shares']:,} ({round(signal['shares'] / 100, 0):,.0f} Lots)")
        print(f"Investment Amount: Rp {signal['investment']:,.0f}")
        print(f"Risk Amount: Rp {signal['risk_amount']:,.0f} ({signal['risk_percent']:.2f}%)")
        print(f"Max Hold Period: {signal['max_hold_days']} days")
    else:
        print(f"\n⏳ NO SIGNAL - Wait for better entry")

    # Pivot Points
    print(f"\nPivot Point: Rp {signal['pivot_point']:,.0f} {signal['pivot_point_status']}")
    print(f"R1 Level: Rp {signal['r1_level']:,.0f} {signal['r1_status']}")
    print(f"R2 Level: Rp {signal['r2_level']:,.0f} {signal['r2_status']}")
    print(f"R3 Level: Rp {signal['r3_level']:,.0f} {signal['r3_status']}")
    print(f"S1 Level: Rp {signal['s1_level']:,.0f} {signal['s1_status']}")
    print(f"S2 Level: Rp {signal['s2_level']:,.0f} {signal['s2_status']}")
    print(f"S3 Level: Rp {signal['s3_level']:,.0f} {signal['s3_status']}")

    # RSI Analysis
    rsi = signal['rsi14']
    print(f"\n📊 TECHNICAL ANALYSIS:")
    print(f"RSI(14): {rsi:.1f}", end="")
    if rsi >= 70:
        print(" 🔴 OVERBOUGHT - Consider selling pressure")
    elif rsi <= 30:
        print(" 🟢 OVERSOLD - Potential bounce opportunity")
    elif rsi >= 60:
        print(" 🟡 BULLISH MOMENTUM - Strong uptrend")
    elif rsi <= 40:
        print(" 🟡 BEARISH MOMENTUM - Weak trend")
    else:
        print(" ⚪ NEUTRAL - No strong momentum")
    
    # ATR Analysis
    atr = signal['atr14']
    price = signal['current_price']
    atr_percent = (atr / price) * 100
    print(f"ATR(14): Rp {atr:,.0f} ({atr_percent:.1f}% of price)", end="")
    if atr_percent >= 5:
        print(" 🔥 HIGH VOLATILITY - Large price swings expected")
    elif atr_percent >= 3:
        print(" 🟡 MODERATE VOLATILITY - Normal market movement")
    else:
        print(" 🟢 LOW VOLATILITY - Stable price action")
    
    # Combined RSI + ATR insight
    print(f"\n💡 MARKET CONDITION:")
    if rsi >= 70 and atr_percent >= 4:
        print("⚠️  Overbought + High Volatility - Risk of sharp pullback")
    elif rsi <= 30 and atr_percent >= 4:
        print("🎯 Oversold + High Volatility - Strong bounce potential")
    elif rsi >= 60 and atr_percent <= 2:
        print("📈 Strong trend + Low volatility - Steady upward movement")
    elif rsi <= 40 and atr_percent <= 2:
        print("📉 Weak trend + Low volatility - Consolidation phase")
    elif atr_percent >= 5:
        print("🌪️  Very high volatility - Exercise extra caution")
    else:
        print("⚖️  Balanced conditions - Standard risk management applies")
    
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Live Signal Generator for Indonesian Stocks')
    parser.add_argument('--symbol', type=str, default='WIFI.JK', 
                       help='Stock symbol (default: WIFI.JK). Examples: BBCA.JK, GOTO.JK, TLKM.JK')
    parser.add_argument('--cash', type=float, default=1_000_000, help='Available cash (default: 1,000,000)')
    parser.add_argument('--strategy', choices=['breakout', 'resistance_retest', 'pullback', 'all'], default='all', 
                       help='Strategy to check (default: all)')
    args = parser.parse_args()
    
    try:
        # Fetch latest data
        df = load_ohlcv(args.symbol, "2023-01-01")
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Check signals
        if args.strategy in ['breakout', 'all']:
            breakout_signal = check_breakout_signal(df, args.symbol, args.cash)
            display_signal(breakout_signal)
        
        if args.strategy in ['resistance_retest', 'all']:
            resistance_retest_signal = check_resistance_retest_signal(df, args.symbol, args.cash)
            display_signal(resistance_retest_signal)
        
        if args.strategy in ['pullback', 'all']:
            pullback_signal = check_pullback_signal(df, args.symbol, args.cash)
            display_signal(pullback_signal)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have internet connection and the investiny package installed")
        print("Install investiny with: pip install git+https://github.com/fajardm/investiny.git")
        print("Valid Indonesian stock symbols should end with .JK (e.g., BBCA.JK)")


if __name__ == '__main__':
    main()