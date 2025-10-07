import pandas as pd
import datetime as dt
import os
from pathlib import Path
from typing import Optional
from investiny import search_assets, historical_data
import pytz

# Configuration will be loaded when first used
_config = None

def get_config():
    """Get configuration instance (lazy loading to avoid circular imports)"""
    global _config
    if _config is None:
        from config import get_config as _get_config
        _config = _get_config()
    return _config

# Create cache directory
CACHE_DIR = Path(__file__).parent / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_filename(ticker: str, start_date: str) -> str:
    """Generate cache filename based on ticker and start date"""
    # Remove .JK suffix for filename
    clean_ticker = ticker.replace('.JK', '')
    return f"{clean_ticker}_{start_date}_data.csv"

def load_from_cache(ticker: str, start_date: str) -> Optional[pd.DataFrame]:
    """Load data from CSV cache if exists and is recent"""
    cache_file = CACHE_DIR / get_cache_filename(ticker, start_date)
    
    if not cache_file.exists():
        print(f"📁 No cache found for {ticker}")
        return None
    
    try:
        # Check cache age (refresh only during trading hours)
        # Get current time in configured timezone
        config = get_config()
        wib_tz = pytz.timezone(config.timezone)
        now_wib = dt.datetime.now(wib_tz)
        
        file_age = now_wib - dt.datetime.fromtimestamp(cache_file.stat().st_mtime, tz=wib_tz)
        
        # Check if it's trading hours (Monday-Friday, configurable hours)
        is_weekday = now_wib.weekday() < 5  # Monday=0, Friday=4
        is_trading_hours = config.trading_start_hour <= now_wib.hour < config.trading_end_hour
        
        print(f"🕒 Current time {config.timezone}: {now_wib.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"📅 Weekday: {is_weekday}, Trading hours: {is_trading_hours} ({config.trading_start_hour}:00-{config.trading_end_hour}:00)")
        
        if is_weekday and is_trading_hours:
            # During trading hours: refresh if older than configured minutes
            refresh_threshold = config.cache_refresh_interval_minutes * 60  # Convert to seconds
            if file_age.total_seconds() > refresh_threshold:
                minutes_old = file_age.total_seconds() / 60
                print(f"🔄 Cache for {ticker} is {minutes_old:.1f} minutes old, refreshing (threshold: {config.cache_refresh_interval_minutes} min)...")
                return None
        else:
            # Outside trading hours: use cache regardless of age
            hours_old = file_age.total_seconds() / 3600
            print(f"📁 Using cache for {ticker} (outside trading hours, {hours_old:.1f}h old)")
        
        # Load cache data (either during trading hours and within 10 min, or outside trading hours)
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        print(f"📁 Loaded {ticker} from cache ({len(df)} rows)")
        return df
        
    except Exception as e:
        print(f"❌ Failed to load cache for {ticker}: {e}")
        return None

def save_to_cache(df: pd.DataFrame, ticker: str, start_date: str):
    """Save data to CSV cache"""
    try:
        cache_file = CACHE_DIR / get_cache_filename(ticker, start_date)
        df.to_csv(cache_file)
        print(f"💾 Saved {ticker} to cache ({len(df)} rows)")
    except Exception as e:
        print(f"❌ Failed to save cache for {ticker}: {e}")

def get_investiny_id(ticker: str) -> Optional[int]:
    """
    Search for a ticker symbol and return the best matching investiny ID.
    """
    try:
        # Handle Indonesian stocks (.JK suffix)
        search_ticker = ticker.replace('.JK', '')
        print(f"🔍 Searching for ticker: {search_ticker}")
        
        results = search_assets(search_ticker)
        
        if not results:
            print(f"❌ No results found for ticker {ticker}")
            return None
        
        # Filter for Jakarta exchange
        filtered = [r for r in results if r.get('exchange') == 'Jakarta']
        
        if filtered:
            asset_id = int(filtered[0]['ticker'])
            print(f"✅ Found {ticker} with ID: {asset_id}")
            return asset_id
        else:
            print(f"❌ No Jakarta exchange results for {ticker}")
            return None
            
    except Exception as e:
        print(f"❌ Error searching for {ticker}: {e}")
        return None


def load_ohlcv(ticker: str, start: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Load OHLCV data with CSV cache mechanism.
    Priority: Cache -> Live API -> Fallback
    """
    if not start:
        start = '2024-01-01'
    
    print(f"📊 Loading OHLCV data for {ticker}...")
    
    # Try loading from cache first
    cached_data = load_from_cache(ticker, start)
    if cached_data is not None:
        return cached_data
    
    # If no cache, try live API
    print(f"🌐 Fetching live data for {ticker} from API...")
    
    try:
        # Get investiny ID
        investiny_id = get_investiny_id(ticker)
        if not investiny_id:
            print(f"❌ Could not get investiny ID for {ticker}")
            return None
        
        # Convert dates to investiny format
        start_date = pd.to_datetime(start).strftime('%m/%d/%Y')
        end_date = pd.Timestamp.now().strftime('%m/%d/%Y')
        
        print(f"📈 Fetching historical data from {start_date} to {end_date}...")
        data = historical_data(investiny_id, start_date, end_date)
        
        if not data:
            print(f"❌ No historical data returned for {ticker}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        # Save to cache for future use
        save_to_cache(df, ticker, start)
        
        print(f"✅ Successfully loaded {len(df)} rows for {ticker}")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching live data for {ticker}: {e}")
        
        # Try to use any existing cache even if old
        print(f"🔄 Trying to use any existing cache for {ticker}...")
        cache_file = CACHE_DIR / get_cache_filename(ticker, start)
        if cache_file.exists():
            try:
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                print(f"📁 Using old cache for {ticker} ({len(df)} rows)")
                return df
            except Exception as cache_error:
                print(f"❌ Failed to load old cache: {cache_error}")
        
        return None

def list_cache_files():
    """List all cached data files"""
    print(f"📁 Cache Directory: {CACHE_DIR}")
    cache_files = list(CACHE_DIR.glob("*.csv"))
    
    if not cache_files:
        print("📁 No cache files found")
        return
    
    print(f"📁 Found {len(cache_files)} cache files:")
    for file in cache_files:
        # Get file stats
        file_age = dt.datetime.now() - dt.datetime.fromtimestamp(file.stat().st_mtime)
        file_size = file.stat().st_size / 1024  # KB
        
        print(f"  • {file.name} ({file_size:.1f} KB, {file_age.days} days old)")


def clear_cache():
    """Clear all cache files"""
    cache_files = list(CACHE_DIR.glob("*.csv"))
    
    if not cache_files:
        print("📁 No cache files to clear")
        return
    
    for file in cache_files:
        file.unlink()
    
    print(f"🗑️ Cleared {len(cache_files)} cache files")


if __name__ == "__main__":
    # Test cache mechanism
    print("🧪 Testing Cache Mechanism")
    print("=" * 40)
    
    # List current cache
    list_cache_files()
    
    # Test data loading
    print("\n📊 Testing data loading for WIFI.JK...")
    df = load_ohlcv("WIFI.JK", start="2024-01-01")
    
    if df is not None:
        print(f"✅ Successfully loaded {len(df)} rows")
        print(f"📅 Date range: {df.index[0]} to {df.index[-1]}")
        print(f"💰 Price range: {df['close'].min():.0f} - {df['close'].max():.0f}")
    else:
        print("❌ Failed to load data")
    
    # Show cache status
    print("\n📁 Cache status after loading:")
    list_cache_files()