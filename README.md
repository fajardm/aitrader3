# AI Trader 3 - Indonesian Stock Trading System

A comprehensive backtesting and live trading signal system for Indonesian stocks, featuring advanced risk management, technical analysis, and real-time signal generation.

## 🚀 Features

- **Realistic Backtesting**: Portfolio simulation with proper cash management and position sizing
- **Live Signal Generation**: Real-time trading signals for any Indonesian stock
- **Advanced Risk Management**: 2% risk per trade with ATR-based stop loss/take profit
- **Technical Analysis**: EMA, RSI, ATR, and classic pivot point indicators
- **Multi-Ticker Support**: Works with any Indonesian stock symbol
- **Dual Data Sources**: Investiny (primary) and YFinance (fallback)

## 📊 Strategy Performance

The system implements two proven strategies:
- **Pullback Strategy**: Entry on pullback to support levels
- **Breakout Strategy**: Entry on breakout above resistance levels

**Backtest Results (WIFI.JK)**:
- **Total Return**: 46.8%
- **Maximum Drawdown**: 8.0%
- **Risk per Trade**: 2% of capital
- **Initial Capital**: Rp 1,000,000

## 🛠️ Installation

### 1. Clone and Setup Virtual Environment

```bash
cd /path/to/your/workspace
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Investiny (Indonesian Stock Data)

```bash
pip install git+https://github.com/fajardm/investiny.git
```

## 📁 Project Structure

```
aitrader3/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── realistic_backtest.py     # Main backtesting system
├── live_signal.py           # Real-time signal generator
├── fetch_data.py            # Data fetching utilities
└── venv/                    # Virtual environment (created after setup)
```

## 🎯 Usage

### Running Backtests

Test any Indonesian stock with customizable parameters:

```bash
python realistic_backtest.py
```

**Configuration Options:**
- Change ticker symbol in the script (default: WIFI.JK)
- Adjust risk percentage (default: 2%)
- Modify initial capital (default: Rp 1,000,000)
- Set backtest period (default: 1 year)

### Live Signal Generation

Get real-time trading signals:

```bash
python live_signal.py
```

**Features:**
- Real-time data fetching
- Entry/exit signal detection
- Position sizing recommendations
- Stop loss/take profit levels
- Market timing guidance

**Example Output:**
```
=== WIFI.JK Live Signal Analysis ===
Current Price: Rp 1,850
Signal: STRONG BUY (Breakout)
Entry Price: Rp 1,850
Stop Loss: Rp 1,795
Take Profit: Rp 1,960
Position Size: 540 shares (Rp 999,000)
Risk Amount: Rp 19,980 (2.0%)
```

### Data Fetching

Fetch and save historical data:

```bash
python fetch_data.py --symbol WIFI.JK --days 365 --out WIFI_data.csv
```

## 🔧 Configuration

### Risk Management Settings

Edit `realistic_backtest.py` to adjust:
- `risk_per_trade = 0.02` (2% risk per trade)
- `initial_cash = 1000000` (Starting capital)
- `atr_multiplier = 2.0` (Stop loss distance)

### Technical Indicators

The system uses:
- **EMA Periods**: 5, 10, 20, 50, 100, 200
- **RSI Period**: 14
- **ATR Period**: 14
- **Pivot Points**: Classic (R1, R2, R3, S1, S2, S3)

### Supported Tickers

Works with any Indonesian stock listed on IDX:
- WIFI.JK (PT Solusi Bangun Indonesia)
- BBCA.JK (Bank Central Asia)
- BMRI.JK (Bank Mandiri)
- TLKM.JK (Telkom Indonesia)
- And many more...

## 📈 Strategy Logic

### Entry Conditions

**Breakout Strategy:**
- Price closes above R3 pivot level
- RSI < 70 (not overbought)
- Volume confirmation
- EMA trend alignment

**Pullback Strategy:**
- Price bounces from R2 support
- RSI > 30 (not oversold)
- Bullish EMA crossover
- Momentum confirmation

### Exit Conditions

- **Stop Loss**: 2x ATR below entry price
- **Take Profit**: 3x ATR above entry price
- **Risk Management**: Maximum 2% capital risk per trade

## 🔍 Monitoring

### Live Signals

The system provides:
- **Entry Timing**: Optimal entry points based on technical analysis
- **Risk Assessment**: Calculated position size and risk amount
- **Exit Levels**: Predetermined stop loss and take profit levels
- **Market Context**: Current trend and momentum analysis

### Performance Tracking

Monitor your trading performance:
- Individual trade results
- Cumulative returns
- Drawdown analysis
- Win rate and risk-reward ratios

## ⚠️ Disclaimer

This trading system is for educational and research purposes only. Past performance does not guarantee future results. Always:

- Test strategies thoroughly before live trading
- Never risk more than you can afford to lose
- Consider consulting with financial advisors
- Understand that all trading involves risk

## 🤝 Contributing

Feel free to submit issues, feature requests, or improvements to enhance the trading system.

## 📄 License

This project is for personal and educational use. Please respect all applicable financial regulations and terms of service for data providers.

## 🚅 Deploying to Railway (quick note)

To deploy this Flask app to Railway:

1. Commit and push your repo to GitHub.
2. Create a new project on Railway and connect the repo.
3. Railway will detect a Python app. Ensure `requirements.txt` is present and `Procfile` contains:

```
web: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
```

4. Railway provides `PORT` automatically. Optionally set `FLASK_DEBUG=0` for production.
5. Deploy and monitor logs from Railway's dashboard.

Note: If `investiny` installation requires Git dependencies, Railway will install them from `requirements.txt` which already references the Git URL.

## ☁️ Deploying to Google Cloud Run

This project includes a `Dockerfile` and `cloudbuild.yaml` to build and deploy to Cloud Run using Cloud Build.

Quick steps (gcloud must be installed and authenticated):

1. Enable required APIs:

```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
```

2. Submit a Cloud Build (from repo root):

```bash
gcloud builds submit --config cloudbuild.yaml --substitutions=_COMMIT_SHA=$(git rev-parse --short HEAD)
```

3. Alternatively build & push manually, then deploy:

```bash
docker build -t gcr.io/$GOOGLE_CLOUD_PROJECT/aitrader3:latest .
docker push gcr.io/$GOOGLE_CLOUD_PROJECT/aitrader3:latest
gcloud run deploy aitrader3 --image gcr.io/$GOOGLE_CLOUD_PROJECT/aitrader3:latest --region us-central1 --platform managed --allow-unauthenticated
```

Notes:
- Cloud Run sets the `PORT` environment variable automatically; the `Dockerfile` and `app.py` already respect that.
- If you need to set environment variables (API keys, FLASK_DEBUG=0), configure them in Cloud Run after deployment or add `--set-env-vars` to the `gcloud run deploy` command.
