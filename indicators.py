"""
Technical Indicators Module
==========================

Centralized technical indicators calculation for all trading strategies.
This module ensures consistent indicator calculation across backtesting and live trading.
"""

import pandas as pd
import ta


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators needed for trading strategies
    
    Args:
        df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        
    Returns:
        DataFrame with added technical indicators
    """
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # EMAs (Exponential Moving Averages)
    df['ema5'] = ta.trend.ema_indicator(df['close'], window=5)
    df['ema10'] = ta.trend.ema_indicator(df['close'], window=10)
    df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['ema100'] = ta.trend.ema_indicator(df['close'], window=100)
    df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
    
    # Momentum Indicators
    df['rsi14'] = ta.momentum.rsi(df['close'], window=14)
    
    # Volatility Indicators
    df['atr14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    
    # Classic Pivot Points (using previous day's OHLC)
    df['P'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['R1'] = 2 * df['P'] - df['low'].shift(1)
    df['R2'] = df['P'] + (df['high'].shift(1) - df['low'].shift(1))
    df['R3'] = df['high'].shift(1) + 2 * (df['P'] - df['low'].shift(1))
    df['S1'] = 2 * df['P'] - df['high'].shift(1)
    df['S2'] = df['P'] - (df['high'].shift(1) - df['low'].shift(1))
    df['S3'] = df['low'].shift(1) - 2 * (df['high'].shift(1) - df['P'])
    
    return df


def validate_indicators(df: pd.DataFrame) -> bool:
    """
    Validate that all required indicators are present in the DataFrame
    
    Args:
        df: DataFrame to validate
        
    Returns:
        True if all indicators are present, False otherwise
    """
    required_indicators = [
        'ema5', 'ema10', 'ema20', 'ema50', 'ema100', 'ema200',
        'rsi14', 'atr14',
        'P', 'R1', 'R2', 'R3', 'S1', 'S2', 'S3'
    ]
    
    missing_indicators = [col for col in required_indicators if col not in df.columns]
    
    if missing_indicators:
        print(f"❌ Missing indicators: {missing_indicators}")
        return False
    
    return True


def get_indicator_summary(df: pd.DataFrame) -> dict:
    """
    Get summary of current indicator values for the latest data point
    
    Args:
        df: DataFrame with indicators
        
    Returns:
        Dict with current indicator values
    """
    if df.empty:
        return {}
    
    latest = df.iloc[-1]
    
    return {
        'date': latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
        'close': latest['close'],
        'pivot_point': latest['P'],
        'resistance_levels': {
            'R1': latest['R1'],
            'R2': latest['R2'], 
            'R3': latest['R3']
        },
        'support_levels': {
            'S1': latest['S1'],
            'S2': latest['S2'],
            'S3': latest['S3']
        },
        'trend_indicators': {
            'ema10': latest['ema10'],
            'ema20': latest['ema20'],
            'ema50': latest['ema50']
        },
        'momentum': {
            'rsi14': latest['rsi14']
        },
        'volatility': {
            'atr14': latest['atr14']
        }
    }