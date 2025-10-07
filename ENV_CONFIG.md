# Environment Configuration Guide

This project uses `.env` files to manage configuration settings. This approach provides flexibility for different environments (development, testing, production) without changing code.

## 📁 Files

- `.env.example` - Template file with all available settings and documentation
- `.env` - Your actual configuration file (not committed to git)

## 🚀 Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your settings:**
   ```bash
   nano .env
   ```

3. **Install python-dotenv** (if not already installed):
   ```bash
   pip install python-dotenv
   ```

## ⚙️ Configuration Options

### Cache Settings
```env
CACHE_REFRESH_INTERVAL_MINUTES=10  # How often to refresh during trading hours
TRADING_START_HOUR=9               # Market open hour (WIB)
TRADING_END_HOUR=18                # Market close hour (WIB)
TIMEZONE=Asia/Jakarta              # Timezone for trading hours
```

### Flask Settings
```env
FLASK_ENV=development              # development|production
FLASK_DEBUG=True                   # Enable/disable debug mode
SECRET_KEY=your-secret-key-here    # Change this in production!
```

### Trading Settings
```env
DEFAULT_START_DATE=2024-01-01      # Default backtest start date
DEFAULT_INITIAL_CASH=1000000       # Default initial capital (Rp)
DEFAULT_RISK_PERCENT=0.02          # Default risk per trade (2%)
```

### Data Settings
```env
MAX_CACHE_AGE_HOURS=24            # Maximum cache age before fallback
```

## 🌍 Environment-Specific Configurations

### Development
```env
FLASK_ENV=development
FLASK_DEBUG=True
CACHE_REFRESH_INTERVAL_MINUTES=2
TRADING_START_HOUR=8
TRADING_END_HOUR=20
```

### Production
```env
FLASK_ENV=production
FLASK_DEBUG=False
CACHE_REFRESH_INTERVAL_MINUTES=10
TRADING_START_HOUR=9
TRADING_END_HOUR=18
SECRET_KEY=your-super-secure-production-key
```

### Testing
```env
FLASK_ENV=testing
FLASK_DEBUG=False
CACHE_REFRESH_INTERVAL_MINUTES=1
DEFAULT_INITIAL_CASH=100000
```

## 🔒 Security Notes

1. **Never commit `.env` to git** - it contains sensitive data
2. **Use strong SECRET_KEY in production**
3. **Different keys for different environments**
4. **Keep `.env.example` updated** but without real secrets

## 🛠️ Usage in Code

The configuration is automatically loaded when modules are imported:

```python
from fetch_data import load_ohlcv  # Automatically uses .env config
from app import app               # Flask app with .env settings

# Or access directly:
import os
from dotenv import load_dotenv
load_dotenv()

cache_interval = int(os.getenv('CACHE_REFRESH_INTERVAL_MINUTES', 10))
```

## 🎛️ Dynamic Configuration

You can also change settings at runtime:

```python
from fetch_data import set_cache_config

# Override .env settings
set_cache_config(refresh_minutes=5, start_hour=8, end_hour=17)
```

## 🧪 Testing Configuration

For testing different scenarios:

```bash
# Test with 1-minute refresh
echo "CACHE_REFRESH_INTERVAL_MINUTES=1" > .env.test

# Test with extended hours
echo "TRADING_START_HOUR=7" >> .env.test
echo "TRADING_END_HOUR=19" >> .env.test

# Load test config
cp .env.test .env
python app.py
```

## 📊 Monitoring

The application logs the current configuration on startup:

```
🚀 Starting Flask app with debug=True, port=5001
⚙️ Cache config: 10min refresh, 9:00-18:00
🕒 Current time WIB: 2025-10-07 14:30:00 WIB
📅 Weekday: True, Trading hours: True (9:00-18:00)
```

## 🔧 Troubleshooting

### `.env` not found
```bash
cp .env.example .env
```

### Settings not applied
1. Check file syntax (no spaces around `=`)
2. Restart the application
3. Verify file location (same directory as `app.py`)

### Cache not refreshing
1. Check timezone setting: `TIMEZONE=Asia/Jakarta`
2. Verify trading hours: `TRADING_START_HOUR=9`
3. Check current time vs trading hours in logs