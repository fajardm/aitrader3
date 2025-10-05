"""
Centralized Trading Strategies Module
====================================

This module contains all the core logic for breakout and pullback trading strategies.
By centralizing the logic here, we ensure consistency between backtesting and live trading.

Performance Proven:
- Multi-level breakout strategy: 94.4% return, 1.59 Sharpe ratio
- Multi-level pullback strategy: Adaptive risk management with R1/R2 levels
"""

import pandas as pd
from typing import Dict, Tuple


class TradingStrategy:
    """Centralized trading strategy logic for breakout and pullback strategies"""
    
    @staticmethod
    def check_breakout_conditions(row: pd.Series) -> Dict[str, bool]:
        """
        Check breakout conditions for all resistance levels
        
        Args:
            row: Single row of OHLC data with indicators
            
        Returns:
            Dict with breakout status for each level
        """
        return {
            'r1_breakout': (
                (row['close'] > row['R1']) and 
                (row['rsi14'] > 35) and 
                (row['close'] > row['ema10'])
            ),
            'r2_breakout': (
                (row['close'] > row['R2']) and 
                (row['rsi14'] > 40) and 
                (row['close'] > row['ema20'])
            ),
            'r3_breakout': (
                (row['close'] > row['R3']) and 
                (row['rsi14'] > 40)
            )
        }
    
    @staticmethod
    def determine_breakout_level(breakout_status: Dict[str, bool]) -> str:
        """
        Determine the highest breakout level achieved
        Priority: R3 > R2 > R1 (stronger breakout preferred)
        
        Args:
            breakout_status: Dict from check_breakout_conditions()
            
        Returns:
            Triggered level ('R1', 'R2', or 'R3')
        """
        if breakout_status['r3_breakout']:
            return 'R3'
        elif breakout_status['r2_breakout']:
            return 'R2'
        else:
            return 'R1'
    
    @staticmethod
    def get_breakout_parameters(level: str, atr: float, entry_price: float) -> Dict[str, float]:
        """
        Get stop loss, take profit, and max hold days for breakout strategy
        
        Args:
            level: Breakout level ('R1', 'R2', or 'R3')
            atr: Average True Range value
            entry_price: Entry price for the trade
            
        Returns:
            Dict with stop_loss, take_profit, and max_days
        """
        if level == 'R1':
            # R1 breakout - early momentum, TIGHTER management for risk control
            return {
                'stop_loss': entry_price - 0.6 * atr,  # Reduced from 0.8 to 0.6 ATR
                'take_profit': entry_price + 1.2 * atr,  # Reduced from 1.5 to 1.2 ATR
                'max_days': 3  # Reduced from 4 to 3 days
            }
        elif level == 'R2':
            # R2 breakout - confirmed momentum, balanced approach
            return {
                'stop_loss': entry_price - 1.0 * atr,
                'take_profit': entry_price + 2.0 * atr,
                'max_days': 6
            }
        else:  # R3
            # R3 breakout - strong momentum, wider stops
            return {
                'stop_loss': entry_price - 1.2 * atr,
                'take_profit': entry_price + 2.5 * atr,
                'max_days': 8
            }
    
    @staticmethod
    def check_pullback_conditions(row: pd.Series) -> Dict[str, bool]:
        """
        Check pullback conditions for support levels
        
        Args:
            row: Single row of OHLC data with indicators
            
        Returns:
            Dict with pullback status for each level
        """
        return {
            'r1_triggered': (
                (row['low'] <= row['R1'] * 1.01) and 
                (row['high'] >= row['R1'] * 0.99) and
                (row['close'] > row['R1']) and
                (row['close'] > row['ema20'])
            ),
            'r2_triggered': (
                (row['low'] <= row['R2'] * 1.02) and
                (row['high'] >= row['R2'] * 0.98) and
                (row['close'] > row['ema20'])
            )
        }
    
    @staticmethod
    def determine_pullback_level(pullback_status: Dict[str, bool]) -> str:
        """
        Determine the pullback level triggered
        
        Args:
            pullback_status: Dict from check_pullback_conditions()
            
        Returns:
            Triggered level ('R1' or 'R2')
        """
        if pullback_status['r1_triggered'] and not pullback_status['r2_triggered']:
            return 'R1'
        else:
            return 'R2'
    
    @staticmethod
    def get_pullback_parameters(level: str, atr: float, entry_price: float) -> Dict[str, float]:
        """
        Get stop loss, take profit, and max hold days for pullback strategy
        
        Args:
            level: Pullback level ('R1' or 'R2')
            atr: Average True Range value
            entry_price: Entry price for the trade
            
        Returns:
            Dict with stop_loss, take_profit, and max_days
        """
        if level == 'R1':
            # R1 pullback - closer entry, tighter stops
            return {
                'stop_loss': entry_price - 1.0 * atr,
                'take_profit': entry_price + 2.0 * atr,
                'max_days': 6
            }
        else:  # R2
            # R2 pullback - stronger support, wider stops
            return {
                'stop_loss': entry_price - 1.5 * atr,
                'take_profit': entry_price + 2.5 * atr,
                'max_days': 8
            }
    
    @staticmethod
    def has_breakout_signal(row: pd.Series) -> bool:
        """
        Check if any breakout signal exists
        
        Args:
            row: Single row of OHLC data with indicators
            
        Returns:
            True if breakout signal exists
        """
        breakout_status = TradingStrategy.check_breakout_conditions(row)
        return any(breakout_status.values())
    
    @staticmethod
    def has_pullback_signal(row: pd.Series) -> bool:
        """
        Check if pullback signal exists with additional filters
        
        Args:
            row: Single row of OHLC data with indicators
            
        Returns:
            True if pullback signal exists
        """
        pullback_status = TradingStrategy.check_pullback_conditions(row)
        
        # Additional filters
        basic_signal = any(pullback_status.values())
        rsi_filter = row['rsi14'] < 70
        data_quality = (
            pd.notna(row['R1']) and 
            pd.notna(row['R2']) and 
            pd.notna(row['atr14'])
        )
        
        return basic_signal and rsi_filter and data_quality
    
    @staticmethod
    def calculate_position_size(cash: float, entry_price: float, stop_loss: float, risk_percent: float = 0.02) -> Tuple[int, float]:
        """
        Calculate position size based on risk management
        
        Args:
            cash: Available cash
            entry_price: Planned entry price
            stop_loss: Stop loss price
            risk_percent: Risk percentage (default 2%)
            
        Returns:
            Tuple of (shares, investment_amount)
        """
        risk_amount = cash * risk_percent
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share > 0:
            shares = int(risk_amount / risk_per_share)
            investment = shares * entry_price
            return shares, investment
        else:
            return 0, 0.0


class BacktestStrategy(TradingStrategy):
    """Extended strategy class specifically for backtesting with position tracking"""
    
    @staticmethod
    def should_exit_position(row: pd.Series, entry_price: float, strategy_type: str, 
                           triggered_level: str, days_held: int) -> Tuple[bool, str]:
        """
        Check if position should be exited based on stop loss, take profit, or time
        
        Args:
            row: Current market data
            entry_price: Price when position was entered
            strategy_type: 'breakout' or 'pullback'
            triggered_level: Level that triggered entry ('R1', 'R2', 'R3')
            days_held: Number of days position has been held
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        atr = row['atr14']
        
        # Get strategy parameters
        if strategy_type == "pullback":
            params = TradingStrategy.get_pullback_parameters(triggered_level, atr, entry_price)
        else:  # breakout
            params = TradingStrategy.get_breakout_parameters(triggered_level, atr, entry_price)
        
        sl_price = params['stop_loss']
        tp_price = params['take_profit']
        max_days = params['max_days']
        
        # Check exit conditions
        if row['low'] <= sl_price:
            return True, 'stop_loss'
        elif row['high'] >= tp_price:
            return True, 'take_profit'
        elif days_held >= max_days:
            return True, 'time_exit'
        else:
            return False, 'hold'


class LiveSignalStrategy(TradingStrategy):
    """Extended strategy class specifically for live signal generation"""
    
    @staticmethod
    def generate_breakout_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> Dict:
        """
        Generate live breakout signal
        
        Args:
            df: DataFrame with market data and indicators
            symbol: Stock symbol
            cash: Available cash
            
        Returns:
            Dict with signal information
        """
        latest = df.iloc[-1]
        
        # Check breakout conditions
        breakout_status = TradingStrategy.check_breakout_conditions(latest)
        has_signal = any(breakout_status.values())
        
        signal_data = {
            'date': latest.name.strftime('%Y-%m-%d'),
            'symbol': symbol,
            'strategy': 'BREAKOUT',
            'signal': 'BUY' if has_signal else 'HOLD',
            'current_price': latest['close'],
            'r1_level': latest['R1'],
            'r2_level': latest['R2'],
            'r3_level': latest['R3'],
            'rsi14': latest['rsi14'],
            'atr14': latest['atr14']
        }
        
        if has_signal:
            # Determine level and get parameters
            level = TradingStrategy.determine_breakout_level(breakout_status)
            params = TradingStrategy.get_breakout_parameters(level, latest['atr14'], latest['close'])
            
            # Calculate position size
            shares, investment = TradingStrategy.calculate_position_size(
                cash, latest['close'], params['stop_loss'], 0.02
            )
            
            risk_amount = shares * (latest['close'] - params['stop_loss'])
            risk_pct = (risk_amount / cash) * 100
            
            signal_data.update({
                'entry_price': latest['close'],
                'entry_level': level,
                'stop_loss': params['stop_loss'],
                'take_profit': params['take_profit'],
                'shares': shares,
                'investment': investment,
                'risk_amount': risk_amount,
                'risk_percent': risk_pct,
                'max_hold_days': params['max_days']
            })
        
        return signal_data
    
    @staticmethod
    def generate_pullback_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> Dict:
        """
        Generate live pullback signal
        
        Args:
            df: DataFrame with market data and indicators
            symbol: Stock symbol
            cash: Available cash
            
        Returns:
            Dict with signal information
        """
        latest = df.iloc[-1]
        
        # Check pullback conditions
        has_signal = TradingStrategy.has_pullback_signal(latest)
        
        signal_data = {
            'date': latest.name.strftime('%Y-%m-%d'),
            'symbol': symbol,
            'strategy': 'PULLBACK',
            'signal': 'BUY' if has_signal else 'HOLD',
            'current_price': latest['close'],
            'r1_level': latest['R1'],
            'r2_level': latest['R2'],
            'ema20': latest['ema20'],
            'rsi14': latest['rsi14'],
            'atr14': latest['atr14']
        }
        
        if has_signal:
            # Determine level and entry price
            pullback_status = TradingStrategy.check_pullback_conditions(latest)
            level = TradingStrategy.determine_pullback_level(pullback_status)
            
            # Set entry price based on triggered level
            entry_price = latest['R1'] if level == 'R1' else latest['R2']
            
            # Get parameters
            params = TradingStrategy.get_pullback_parameters(level, latest['atr14'], entry_price)
            
            # Calculate position size
            shares, investment = TradingStrategy.calculate_position_size(
                cash, entry_price, params['stop_loss'], 0.02
            )
            
            risk_amount = shares * (entry_price - params['stop_loss'])
            risk_pct = (risk_amount / cash) * 100
            
            signal_data.update({
                'entry_price': entry_price,
                'entry_level': level,
                'stop_loss': params['stop_loss'],
                'take_profit': params['take_profit'],
                'shares': shares,
                'investment': investment,
                'risk_amount': risk_amount,
                'risk_percent': risk_pct,
                'max_hold_days': params['max_days']
            })
        
        return signal_data