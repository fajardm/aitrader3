"""
Configuration Management Module
==============================

This module provides centralized configuration management using environment variables.
All application settings are loaded and validated in one place.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv


class Config:
    """
    Centralized configuration class for the trading application.
    Loads and validates all environment variables with sensible defaults.
    """
    
    def __init__(self):
        """Load environment variables and initialize configuration"""
        load_dotenv()
        self._load_config()
        self._validate_config()
    
    def _load_config(self):
        """Load all configuration from environment variables"""
        
        # Cache Configuration
        self.cache_refresh_interval_minutes = int(os.getenv('CACHE_REFRESH_INTERVAL_MINUTES', 10))
        self.trading_start_hour = int(os.getenv('TRADING_START_HOUR', 9))
        self.trading_end_hour = int(os.getenv('TRADING_END_HOUR', 18))
        self.timezone = os.getenv('TIMEZONE', 'Asia/Jakarta')
        
        # Flask Configuration
        self.flask_debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
        self.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        
        # Data Source Settings
        self.default_start_date = os.getenv('DEFAULT_START_DATE', '2024-01-01')
        
        # Trading Settings
        self.default_initial_cash = int(os.getenv('DEFAULT_INITIAL_CASH', 1000000))
        
        # Stock Symbols
        stock_symbols_env = os.getenv('STOCK_SYMBOLS', 'WIFI.JK')
        self.stock_symbols = [symbol.strip() for symbol in stock_symbols_env.split(',')]
        
        # Server Configuration
        self.port = int(os.getenv('PORT', 5001))
    
    def _validate_config(self):
        """Validate configuration values"""
        
        # Validate trading hours
        if not (0 <= self.trading_start_hour <= 23):
            raise ValueError(f"Invalid TRADING_START_HOUR: {self.trading_start_hour}")
        
        if not (0 <= self.trading_end_hour <= 23):
            raise ValueError(f"Invalid TRADING_END_HOUR: {self.trading_end_hour}")
        
        if self.trading_start_hour >= self.trading_end_hour:
            raise ValueError("TRADING_START_HOUR must be less than TRADING_END_HOUR")
        
        # Validate cache interval
        if self.cache_refresh_interval_minutes <= 0:
            raise ValueError(f"Invalid CACHE_REFRESH_INTERVAL_MINUTES: {self.cache_refresh_interval_minutes}")
        
        # Validate initial cash
        if self.default_initial_cash <= 0:
            raise ValueError(f"Invalid DEFAULT_INITIAL_CASH: {self.default_initial_cash}")
        
        # Validate stock symbols
        if not self.stock_symbols or len(self.stock_symbols) == 0:
            raise ValueError("STOCK_SYMBOLS cannot be empty")
        
        # Check for invalid symbols (basic validation)
        for symbol in self.stock_symbols:
            if not symbol or len(symbol.strip()) == 0:
                raise ValueError(f"Invalid empty stock symbol in STOCK_SYMBOLS")
    
    @property
    def cache_refresh_interval(self) -> int:
        """Get cache refresh interval in seconds"""
        return self.cache_refresh_interval_minutes * 60
    
    def get_cache_config(self) -> dict:
        """Get cache configuration as dictionary"""
        return {
            'refresh_interval_minutes': self.cache_refresh_interval_minutes,
            'trading_start_hour': self.trading_start_hour,
            'trading_end_hour': self.trading_end_hour,
            'timezone': self.timezone
        }
    
    def get_flask_config(self) -> dict:
        """Get Flask configuration as dictionary"""
        return {
            'debug': self.flask_debug,
            'secret_key': self.secret_key,
            'port': self.port
        }
    
    def get_trading_config(self) -> dict:
        """Get trading configuration as dictionary"""
        return {
            'initial_cash': self.default_initial_cash,
            'start_date': self.default_start_date,
            'stock_symbols': self.stock_symbols
        }
    
    def print_config_summary(self):
        """Print configuration summary for debugging"""
        print("⚙️ Configuration Summary")
        print("=" * 50)
        print(f"🕘 Trading Hours: {self.trading_start_hour}:00 - {self.trading_end_hour}:00 {self.timezone}")
        print(f"🔄 Cache Refresh: Every {self.cache_refresh_interval_minutes} minutes")
        print(f"💰 Initial Cash: Rp {self.default_initial_cash:,}")
        print(f"📅 Start Date: {self.default_start_date}")
        print(f"📊 Monitoring: {len(self.stock_symbols)} stocks")
        print(f"🔧 Flask Debug: {self.flask_debug}")
        print(f"🌐 Port: {self.port}")
        
        if len(self.stock_symbols) <= 10:
            print(f"📈 Stocks: {', '.join(self.stock_symbols)}")
        else:
            print(f"📈 Stocks: {', '.join(self.stock_symbols[:5])} ... (+{len(self.stock_symbols)-5} more)")


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance"""
    return config


# Convenience functions for backward compatibility
def get_stock_symbols() -> List[str]:
    """Get list of stock symbols to monitor"""
    return config.stock_symbols


def get_initial_cash() -> int:
    """Get default initial cash amount"""
    return config.default_initial_cash


def get_start_date() -> str:
    """Get default start date"""
    return config.default_start_date


if __name__ == "__main__":
    # Test configuration loading
    print("🧪 Testing Configuration Loading")
    print("=" * 40)
    
    try:
        test_config = Config()
        test_config.print_config_summary()
        print("\n✅ Configuration loaded successfully!")
        
        # Test validation
        print("\n🔍 Testing configuration validation...")
        cache_config = test_config.get_cache_config()
        flask_config = test_config.get_flask_config()
        trading_config = test_config.get_trading_config()
        
        print(f"Cache Config: {cache_config}")
        print(f"Flask Config: {flask_config}")
        print(f"Trading Config: {trading_config}")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")