import pandas as pd
import datetime as dt
import logging
from pathlib import Path
from typing import Optional
from investiny import search_assets, historical_data

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
CACHE_DIR = Path(__file__).parent / "historical_data"
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_filename(ticker: str, start_date: str, end_date: str) -> str:
    """Generate cache filename based on ticker and start date"""
    # Remove .JK suffix for filename
    clean_ticker = ticker.replace('.JK', '')
    return f"{clean_ticker}_{start_date}_{end_date}_data.csv"

def load_from_cache(ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Load data from CSV cache if exists and is recent"""
    cache_file = CACHE_DIR / get_cache_filename(ticker, start_date, end_date)

    if not cache_file.exists():
        logging.info("📁 No cache found for %s", ticker)
        return None
    
    try:
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        col_aliases = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
        }

        for src, dst in col_aliases.items():
            if src in df.columns and dst not in df.columns:
                df[dst] = df[src]

        logging.info("📁 Loaded %s from cache (%d rows)", ticker, len(df))
        return df
        
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logging.error("❌ Failed to load cache for %s: %s", ticker, e)
        return None

def save_to_cache(df: pd.DataFrame, ticker: str, start_date: str, end_date: str):
    """Save data to CSV cache"""
    try:
        cache_file = CACHE_DIR / get_cache_filename(ticker, start_date, end_date)
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


def load_ohlcv(ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Load OHLCV data with CSV cache mechanism.
    Priority: Cache -> Live API -> Fallback
    """
    if not start_date:
        start_date = '2024-01-01'

    if not end_date:
        end_date = '2024-12-31'
    
    logging.info("📊 Loading OHLCV data for %s...", ticker)
    
    # Try loading from cache first
    cached_data = load_from_cache(ticker, start_date, end_date)
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
        start_date_formated = pd.to_datetime(start_date).strftime('%m/%d/%Y')
        end_date_formated = pd.to_datetime(end_date).strftime('%m/%d/%Y')
        
        logging.info("📈 Fetching historical data from %s to %s...", start_date, end_date)
        data = historical_data(investiny_id, start_date_formated, end_date_formated)
        
        if not data:
            logging.warning("❌ No historical data returned for %s", ticker)
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        # Save to cache for future use
        save_to_cache(df, ticker, start_date, end_date)

        col_aliases = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
        }

        for src, dst in col_aliases.items():
            if src in df.columns and dst not in df.columns:
                df[dst] = df[src]
        
        logging.info("✅ Successfully loaded %d rows for %s", len(df), ticker)
        return df
        
    except (ValueError, KeyError, OSError) as e:
        logging.error("❌ Error fetching live data for %s: %s", ticker, e)
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
    df = load_ohlcv("WIFI.JK", start_date="2024-01-01", end_date="2024-12-31")
    
    if df is not None:
        logging.info("✅ Successfully loaded %d rows", len(df))
        logging.info("📅 Date range: %s to %s", df.index[0], df.index[-1])
        logging.info("💰 Price range: %.0f - %.0f", df['close'].min(), df['close'].max())
    else:
        logging.error("❌ Failed to load data")
    
    # Show cache status
    logging.info("\n📁 Cache status after loading:")
    list_cache_files()