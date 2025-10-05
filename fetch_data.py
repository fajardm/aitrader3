import pandas as pd
import datetime as dt
from typing import Optional
from investiny import search_assets, historical_data

def get_investiny_id(ticker: str) -> Optional[int]:
    """
    Search for a ticker symbol and return the best matching investiny ID.
    Prioritizes major exchanges like NASDAQ, NYSE, Jakarta for Indonesian stocks.
    """
    try:
        # Handle Indonesian stocks (.JK suffix)
        search_ticker = ticker.replace('.JK', '')
        results = search_assets(search_ticker)
        if not results:
            return None
        
        filtered = [r for r in results if r.get('exchange') == 'Jakarta']
        
        return int(filtered[0]['ticker'])
        
    except Exception as e:
        print(f"Error searching for ticker {ticker}: {e}")
        return None
    
def load_ohlcv(ticker: str, start: Optional[str]) -> pd.DataFrame:
    """
    Load OHLCV data using investiny (primary) with caching support.
    """
    if not start:
        start = '2020-01-01'
    
    try:
        # Use cached investing_id system
        investiny_id = get_investiny_id(ticker)
        if investiny_id:
            # Convert start date to investiny format (m/d/Y)
            start_date = pd.to_datetime(start).strftime('%m/%d/%Y')
            end_date = pd.Timestamp.now().strftime('%m/%d/%Y')
            
            data = historical_data(investiny_id, start_date, end_date)
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Convert date column
            df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
            df = df.sort_values('date').set_index('date')
            
            # Ensure numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"✓ Loaded {len(df)} records for {ticker} using investiny")
            return df.dropna()
            
    except Exception as e:
        print(f"Investiny failed for {ticker}: {e}")