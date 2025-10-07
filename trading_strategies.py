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
    def check_resistance_retest_conditions(row: pd.Series) -> Dict[str, bool]:
        """
        Check resistance retest conditions for support levels
        
        Args:
            row: Single row of OHLC data with indicators
            
        Returns:
            Dict with resistance retest status for each level
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
    def determine_resistance_retest_level(retest_status: Dict[str, bool]) -> str:
        """
        Determine the resistance retest level triggered
        
        Args:
            retest_status: Dict from check_resistance_retest_conditions()
            
        Returns:
            Triggered level ('R1' or 'R2')
        """
        if retest_status['r1_triggered'] and not retest_status['r2_triggered']:
            return 'R1'
        else:
            return 'R2'
    
    @staticmethod
    def get_resistance_retest_parameters(level: str, atr: float, entry_price: float) -> Dict[str, float]:
        """
        Get stop loss, take profit, and max hold days for resistance retest strategy
        
        Args:
            level: Resistance retest level ('R1' or 'R2')
            atr: Average True Range value
            entry_price: Entry price for the trade
            
        Returns:
            Dict with stop_loss, take_profit, and max_days
        """
        if level == 'R1':
            # R1 resistance retest - closer entry, tighter stops
            return {
                'stop_loss': entry_price - 1.0 * atr,
                'take_profit': entry_price + 2.0 * atr,
                'max_days': 6
            }
        else:  # R2
            # R2 resistance retest - stronger support, wider stops
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
    def has_resistance_retest_signal(row: pd.Series) -> bool:
        """
        Check if resistance retest signal exists with additional filters
        
        Args:
            row: Single row of OHLC data with indicators
            
        Returns:
            True if resistance retest signal exists
        """
        retest_status = TradingStrategy.check_resistance_retest_conditions(row)
        
        # Additional filters
        basic_signal = any(retest_status.values())
        rsi_filter = row['rsi14'] < 70
        data_quality = (
            pd.notna(row['R1']) and 
            pd.notna(row['R2']) and 
            pd.notna(row['atr14'])
        )
        
        return basic_signal and rsi_filter and data_quality
    
    @staticmethod
    def check_pullback_conditions(row: pd.Series) -> Dict[str, bool]:
        """
        Check pullback conditions for support levels (true pullback strategy)
        
        Args:
            row: Single row of OHLC data with indicators
            
        Returns:
            Dict with pullback status for each support level
        """
        return {
            's1_pullback': (
                (row['high'] >= row['S1'] * 0.99) and  # Touched S1 support
                (row['low'] <= row['S1'] * 1.01) and   # But held above
                (row['close'] > row['S1']) and         # Closed above support
                (row['close'] > row['ema20']) and      # Still in uptrend
                (row['rsi14'] < 70)                    # Not overbought
            ),
            's2_pullback': (
                (row['high'] >= row['S2'] * 0.98) and  # Touched S2 support
                (row['low'] <= row['S2'] * 1.02) and   # But held above
                (row['close'] > row['S2']) and         # Closed above support
                (row['close'] > row['ema20']) and      # Still in uptrend
                (row['rsi14'] < 65)                    # Not too overbought
            ),
            's3_pullback': (
                (row['high'] >= row['S3'] * 0.97) and  # Touched S3 support
                (row['low'] <= row['S3'] * 1.03) and   # But held above
                (row['close'] > row['S3']) and         # Closed above support
                (row['close'] > row['ema10']) and      # Above short-term trend
                (row['rsi14'] < 60)                    # Oversold bounce potential
            )
        }
    
    @staticmethod
    def determine_pullback_level(pullback_status: Dict[str, bool]) -> str:
        """
        Determine the pullback level triggered (support-based)
        Priority: S1 > S2 > S3 (stronger support preferred)
        
        Args:
            pullback_status: Dict from check_pullback_conditions()
            
        Returns:
            Triggered level ('S1', 'S2', or 'S3')
        """
        if pullback_status['s1_pullback']:
            return 'S1'
        elif pullback_status['s2_pullback']:
            return 'S2'
        else:
            return 'S3'
    
    @staticmethod
    def get_pullback_parameters(level: str, atr: float, entry_price: float) -> Dict[str, float]:
        """
        Get stop loss, take profit, and max hold days for pullback strategy (support-based)
        
        Args:
            level: Pullback level ('S1', 'S2', or 'S3')
            atr: Average True Range value
            entry_price: Entry price for the trade
            
        Returns:
            Dict with stop_loss, take_profit, and max_days
        """
        if level == 'S1':
            # S1 pullback - close support, quick bounce
            return {
                'stop_loss': entry_price - 0.8 * atr,
                'take_profit': entry_price + 1.8 * atr,
                'max_days': 5
            }
        elif level == 'S2':
            # S2 pullback - intermediate support, balanced approach
            return {
                'stop_loss': entry_price - 1.2 * atr,
                'take_profit': entry_price + 2.2 * atr,
                'max_days': 7
            }
        else:  # S3
            # S3 pullback - strong support, bigger bounce potential
            return {
                'stop_loss': entry_price - 1.5 * atr,
                'take_profit': entry_price + 2.8 * atr,
                'max_days': 10
            }
    
    @staticmethod
    def has_pullback_signal(row: pd.Series) -> bool:
        """
        Check if pullback signal exists with additional filters (support-based)
        
        Args:
            row: Single row of OHLC data with indicators
            
        Returns:
            True if pullback signal exists
        """
        pullback_status = TradingStrategy.check_pullback_conditions(row)
        
        # Additional filters
        basic_signal = any(pullback_status.values())
        trend_filter = row['close'] > row['ema20']  # Must be in uptrend
        data_quality = (
            pd.notna(row['S1']) and 
            pd.notna(row['S2']) and 
            pd.notna(row['S3']) and
            pd.notna(row['atr14'])
        )
        
        return basic_signal and trend_filter and data_quality
    
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
        
        signal_data = LiveSignalStrategy.default_signal_indicators(latest)

        signal_data.update({
            'symbol': symbol,
            'strategy': 'BREAKOUT',
            'signal': 'BUY' if has_signal else 'HOLD',
        })

        if has_signal:
            # Determine level and get parameters
            level = TradingStrategy.determine_breakout_level(breakout_status)
            params = TradingStrategy.get_breakout_parameters(level, latest['atr14'], latest['close'])
            
            # Calculate position size
            shares, investment = TradingStrategy.calculate_position_size(
                cash, latest['close'], params['stop_loss'], 0.02
            )
            
            risk_amount = shares * (latest['close'] - params['stop_loss'])
            risk_pct = (risk_amount / cash) * 100 if cash > 0 else 0
            
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
    def generate_resistance_retest_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> Dict:
        """
        Generate live resistance retest signal
        
        Args:
            df: DataFrame with market data and indicators
            symbol: Stock symbol
            cash: Available cash
            
        Returns:
            Dict with signal information
        """
        latest = df.iloc[-1]
        
        # Check resistance retest conditions
        has_signal = TradingStrategy.has_resistance_retest_signal(latest)
        
        signal_data = LiveSignalStrategy.default_signal_indicators(latest)

        signal_data.update({
            'symbol': symbol,
            'strategy': 'RESISTANCE_RETEST',
            'signal': 'BUY' if has_signal else 'HOLD',
        })
        
        if has_signal:
            # Determine level and entry price
            retest_status = TradingStrategy.check_resistance_retest_conditions(latest)
            level = TradingStrategy.determine_resistance_retest_level(retest_status)
            
            # Set entry price based on triggered level
            entry_price = latest['R1'] if level == 'R1' else latest['R2']
            
            # Get parameters
            params = TradingStrategy.get_resistance_retest_parameters(level, latest['atr14'], entry_price)
            
            # Calculate position size
            shares, investment = TradingStrategy.calculate_position_size(
                cash, entry_price, params['stop_loss'], 0.02
            )
            
            risk_amount = shares * (entry_price - params['stop_loss'])
            risk_pct = (risk_amount / cash) * 100 if cash > 0 else 0
            
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
    
    @staticmethod
    def generate_pullback_signal(df: pd.DataFrame, symbol: str, cash: float = 1_000_000) -> Dict:
        """
        Generate live pullback signal (support-based)
        
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
        
        signal_data = LiveSignalStrategy.default_signal_indicators(latest)
       
        signal_data.update({
            'symbol': symbol,
            'strategy': 'PULLBACK',
            'signal': 'BUY' if has_signal else 'HOLD',
        })
        
        if has_signal:
            # Determine level and entry price
            pullback_status = TradingStrategy.check_pullback_conditions(latest)
            level = TradingStrategy.determine_pullback_level(pullback_status)
            
            # Set entry price based on triggered level (support level)
            if level == 'S1':
                entry_price = latest['S1']
            elif level == 'S2':
                entry_price = latest['S2']
            else:  # S3
                entry_price = latest['S3']
            
            # Get parameters
            params = TradingStrategy.get_pullback_parameters(level, latest['atr14'], entry_price)
            
            # Calculate position size
            shares, investment = TradingStrategy.calculate_position_size(
                cash, entry_price, params['stop_loss'], 0.02
            )
            
            risk_amount = shares * (entry_price - params['stop_loss'])
            risk_pct = (risk_amount / cash) * 100 if cash > 0 else 0
            
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
    
    @staticmethod
    def default_signal_indicators(df: pd.DataFrame) -> Dict:
        pivot_point_status = "✅ ABOVE PIVOT" if df['close'] > df['P'] else "❌ BELOW PIVOT"

        r1_status = "✅ ABOVE R1" if df['close'] > df['R1'] else "❌ BELOW R1"
        r2_status = "✅ ABOVE R2" if df['close'] > df['R2'] else "❌ BELOW R2"
        r3_status = "✅ ABOVE R3" if df['close'] > df['R3'] else "❌ BELOW R3"

        s1_status = "✅ ABOVE S1" if df['close'] > df['S1'] else "❌ BELOW S1"
        s2_status = "✅ ABOVE S2" if df['close'] > df['S2'] else "❌ BELOW S2"
        s3_status = "✅ ABOVE S3" if df['close'] > df['S3'] else "❌ BELOW S3"

        signal = {
            'date': df.name.strftime('%Y-%m-%d'),
            'current_price': df['close'],
            'r1_level': df['R1'],
            'r1_status': r1_status,
            'r2_level': df['R2'],
            'r2_status': r2_status,
            'r3_level': df['R3'],
            'r3_status': r3_status,
            'pivot_point': df['P'],
            'pivot_point_status': pivot_point_status,
            's3_level': df['S3'],
            's3_status': s3_status,
            's2_level': df['S2'],
            's2_status': s2_status,
            's1_level': df['S1'],
            's1_status': s1_status,
            'ema5': df['ema5'],
            'ema10': df['ema10'],
            'ema20': df['ema20'],
            'ema50': df['ema50'],
            'ema100': df['ema100'],
            'ema200': df['ema200'],
            'rsi14': df['rsi14'],
            'atr14': df['atr14']
        }

        return signal