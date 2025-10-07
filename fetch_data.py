import pandas as pd
import datetime as dt
import logging
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
        logging.info("📁 No cache found for %s", ticker)
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
        
        logging.debug("🕒 Current time %s: %s", config.timezone, now_wib.strftime('%Y-%m-%d %H:%M:%S %Z'))
        logging.debug("📅 Weekday: %s, Trading hours: %s (%s:00-%s:00)", is_weekday, is_trading_hours, config.trading_start_hour, config.trading_end_hour)
        
        if is_weekday and is_trading_hours:
            # During trading hours: refresh if older than configured minutes
            refresh_threshold = config.cache_refresh_interval_minutes * 60  # Convert to seconds
            if file_age.total_seconds() > refresh_threshold:
                minutes_old = file_age.total_seconds() / 60
                logging.info("🔄 Cache for %s is %.1f minutes old, refreshing (threshold: %s min)...", ticker, minutes_old, config.cache_refresh_interval_minutes)
                return None
        else:
            # Outside trading hours: use cache regardless of age
            hours_old = file_age.total_seconds() / 3600
            logging.info("📁 Using cache for %s (outside trading hours, %.1fh old)", ticker, hours_old)
        
        # Load cache data (either during trading hours and within 10 min, or outside trading hours)
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        logging.info("📁 Loaded %s from cache (%d rows)", ticker, len(df))
        return df
        
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logging.error("❌ Failed to load cache for %s: %s", ticker, e)
        return None

def save_to_cache(df: pd.DataFrame, ticker: str, start_date: str):
    """Save data to CSV cache"""
    try:
        cache_file = CACHE_DIR / get_cache_filename(ticker, start_date)
        df.to_csv(cache_file)
        logging.info("💾 Saved %s to cache (%d rows)", ticker, len(df))
    except OSError as e:
        logging.error("❌ Failed to save cache for %s: %s", ticker, e)

def get_investiny_id(ticker: str) -> Optional[int]:
    """
    Search for a ticker symbol and return the best matching investiny ID.
    """
    try:
        # Handle Indonesian stocks (.JK suffix)
        search_ticker = ticker.replace('.JK', '')
        logging.debug("🔍 Searching for ticker: %s", search_ticker)
        
        results = search_assets(search_ticker)
        
        if not results:
            logging.warning("❌ No results found for ticker %s", ticker)
            return None
        
        # Filter for Jakarta exchange
        filtered = [r for r in results if r.get('exchange') == 'Jakarta']
        
        if filtered:
            asset_id = int(filtered[0]['ticker'])
            logging.info("✅ Found %s with ID: %s", ticker, asset_id)
            return asset_id
        else:
            logging.warning("❌ No Jakarta exchange results for %s", ticker)
            return None
            
    except Exception as e:
        # Search may raise various runtime errors from the API client; keep broad here
        logging.error("❌ Error searching for %s: %s", ticker, e)
        return None


def load_ohlcv(ticker: str, start: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Load OHLCV data with CSV cache mechanism.
    Priority: Cache -> Live API -> Fallback
    """
    if not start:
        start = '2024-01-01'
    
    logging.info("📊 Loading OHLCV data for %s...", ticker)
    
    # Try loading from cache first
    cached_data = load_from_cache(ticker, start)
    if cached_data is not None:
        return cached_data
    
    # If no cache, try live API
    logging.info("🌐 Fetching live data for %s from API...", ticker)
    
    try:
        # Get investiny ID
        investiny_id = get_investiny_id(ticker)
        if not investiny_id:
            logging.error("❌ Could not get investiny ID for %s", ticker)
            return None
        
        # Convert dates to investiny format
        start_date = pd.to_datetime(start).strftime('%m/%d/%Y')
        end_date = pd.Timestamp.now().strftime('%m/%d/%Y')
        
        logging.info("📈 Fetching historical data from %s to %s...", start_date, end_date)
        data = historical_data(investiny_id, start_date, end_date)
        
        if not data:
            logging.warning("❌ No historical data returned for %s", ticker)
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        # Save to cache for future use
        save_to_cache(df, ticker, start)
        
        logging.info("✅ Successfully loaded %d rows for %s", len(df), ticker)
        return df
        
    except (ValueError, KeyError, OSError) as e:
        logging.error("❌ Error fetching live data for %s: %s", ticker, e)

        # Try to use any existing cache even if old
        logging.info("🔄 Trying to use any existing cache for %s...", ticker)
        cache_file = CACHE_DIR / get_cache_filename(ticker, start)
        if cache_file.exists():
            try:
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                logging.info("📁 Using old cache for %s (%d rows)", ticker, len(df))
                return df
            except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as cache_error:
                logging.error("❌ Failed to load old cache: %s", cache_error)

        return None

def list_cache_files():
    """List all cached data files"""
    logging.info("📁 Cache Directory: %s", CACHE_DIR)
    cache_files = list(CACHE_DIR.glob("*.csv"))
    
    if not cache_files:
        logging.info("📁 No cache files found")
        return
    
    logging.info("📁 Found %d cache files:", len(cache_files))
    for file in cache_files:
        # Get file stats
        file_age = dt.datetime.now() - dt.datetime.fromtimestamp(file.stat().st_mtime)
        file_size = file.stat().st_size / 1024  # KB
        
        logging.info("  • %s (%.1f KB, %d days old)", file.name, file_size, file_age.days)


def clear_cache():
    """Clear all cache files"""
    cache_files = list(CACHE_DIR.glob("*.csv"))
    
    if not cache_files:
        logging.info("📁 No cache files to clear")
        return
    
    for file in cache_files:
        file.unlink()
    
    logging.info("🗑️ Cleared %d cache files", len(cache_files))


if __name__ == "__main__":
    # Test cache mechanism
    logging.info("🧪 Testing Cache Mechanism")
    logging.info("%s", "=" * 40)
    
    # List current cache
    list_cache_files()
    
    # Test data loading
    logging.info("\n📊 Testing data loading for %s...", "WIFI.JK")
    df = load_ohlcv("WIFI.JK", start="2024-01-01")
    
    if df is not None:
        logging.info("✅ Successfully loaded %d rows", len(df))
        logging.info("📅 Date range: %s to %s", df.index[0], df.index[-1])
        logging.info("💰 Price range: %.0f - %.0f", df['close'].min(), df['close'].max())
    else:
        logging.error("❌ Failed to load data")
    
    # Show cache status
    logging.info("\n📁 Cache status after loading:")
    list_cache_files()