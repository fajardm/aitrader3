"""
Simple Flask Frontend for Trading Signals
=========================================

Flask web application with:
- /: List stocks with summary signals
- /stock/{symbol}: Detailed backtest and signal information
"""

from flask import Flask, render_template, jsonify
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from live_signal import check_breakout_signal, check_resistance_retest_signal, check_pullback_signal
from fetch_data import load_ohlcv
from indicators import calculate_indicators
from realistic_backtest import run_realistic_backtest

# Configuration from environment variables
START_DATE = os.getenv('DEFAULT_START_DATE', '2024-01-01')
INITIAL_CASH = int(os.getenv('DEFAULT_INITIAL_CASH', 1000000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Stock symbols to monitor from environment variable
STOCK_SYMBOLS_ENV = os.getenv('STOCK_SYMBOLS', '')
STOCK_SYMBOLS = [symbol.strip() for symbol in STOCK_SYMBOLS_ENV.split(',')]

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Apply cache configuration from environment
cache_refresh_minutes = int(os.getenv('CACHE_REFRESH_INTERVAL_MINUTES', 30))
trading_start_hour = int(os.getenv('TRADING_START_HOUR', 9))
trading_end_hour = int(os.getenv('TRADING_END_HOUR', 18))

print(f"📊 Monitoring {len(STOCK_SYMBOLS)} stocks: {', '.join(STOCK_SYMBOLS)}")

@app.route('/')
def index():
    """Main page showing list of stocks with summary signals"""
    try:
        stocks_data = []
        
        for symbol in STOCK_SYMBOLS:
            try:
                # Get current data
                df = load_ohlcv(symbol, START_DATE)
                if df is None or len(df) < 50:
                    continue
                
                # Calculate indicators
                df = calculate_indicators(df)
                
                # Get live signals
                breakout_signal = check_breakout_signal(df, symbol, INITIAL_CASH)
                resistance_retest_signal = check_resistance_retest_signal(df, symbol, INITIAL_CASH)
                pullback_signal = check_pullback_signal(df, symbol, INITIAL_CASH)
                
                # Get current price and basic info
                current_price = df.iloc[-1]['close']
                rsi = df.iloc[-1]['rsi14']
                
                # Determine overall signal
                overall_signal = "HOLD"
                signal_color = "warning"
                if breakout_signal['signal'] == 'BUY' or resistance_retest_signal['signal'] == 'BUY' or pullback_signal['signal'] == 'BUY':
                    overall_signal = "BUY"
                    signal_color = "success"
                
                stocks_data.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'rsi': rsi,
                    'overall_signal': overall_signal,
                    'signal_color': signal_color,
                    'breakout_signal': breakout_signal['signal'],
                    'resistance_retest_signal': resistance_retest_signal['signal'],
                    'pullback_signal': pullback_signal['signal']
                })
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return render_template('index.html', 
                             stocks=stocks_data, 
                             current_time=current_time)
        
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route('/stock/<symbol>')
def stock_detail(symbol):
    """Detailed view for a specific stock with backtest and signal information"""
    try:
        # Get current data
        df = load_ohlcv(symbol, START_DATE)
        if df is None or len(df) < 50:
            return f"<h1>Error</h1><p>Insufficient data for {symbol}</p>", 404
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Get live signals with full details
        breakout_signal = check_breakout_signal(df, symbol, INITIAL_CASH)
        resistance_retest_signal = check_resistance_retest_signal(df, symbol, INITIAL_CASH)
        pullback_signal = check_pullback_signal(df, symbol, INITIAL_CASH)
        
        # Run backtest
        try:
            resistance_retest_final, resistance_retest_return, resistance_retest_dd, resistance_retest_sharpe = run_realistic_backtest(df, "Resistance_Retest", INITIAL_CASH)
            pullback_final, pullback_return, pullback_dd, pullback_sharpe = run_realistic_backtest(df, "Pullback", INITIAL_CASH)
            breakout_final, breakout_return, breakout_dd, breakout_sharpe = run_realistic_backtest(df, "Breakout", INITIAL_CASH)
            
            backtest_results = {
                'resistance_retest': {
                    'total_return': resistance_retest_return,
                    'max_drawdown': resistance_retest_dd,
                    'sharpe_ratio': resistance_retest_sharpe,
                    'final_capital': resistance_retest_final
                },
                'pullback': {
                    'total_return': pullback_return,
                    'max_drawdown': pullback_dd,
                    'sharpe_ratio': pullback_sharpe,
                    'final_capital': pullback_final
                },
                'breakout': {
                    'total_return': breakout_return,
                    'max_drawdown': breakout_dd,
                    'sharpe_ratio': breakout_sharpe,
                    'final_capital': breakout_final
                }
            }
        except Exception as e:
            print(f"Backtest error for {symbol}: {e}")
            backtest_results = {
                'resistance_retest': {'total_return': 0, 'max_drawdown': 0, 'sharpe_ratio': 0, 'final_capital': INITIAL_CASH},
                'pullback': {'total_return': 0, 'max_drawdown': 0, 'sharpe_ratio': 0, 'final_capital': INITIAL_CASH},
                'breakout': {'total_return': 0, 'max_drawdown': 0, 'sharpe_ratio': 0, 'final_capital': INITIAL_CASH}
            }
        
        # Get current market data
        latest = df.iloc[-1]
        current_price = latest['close']
        r1_level = latest['R1']
        r2_level = latest['R2']
        r3_level = latest['R3']
        s1_level = latest['S1']
        s2_level = latest['S2']
        s3_level = latest['S3']
        ema5 = latest['ema5'] if 'ema5' in latest else None
        ema10 = latest['ema10'] if 'ema10' in latest else None
        ema20 = latest['ema20']
        ema50 = latest['ema50'] if 'ema50' in latest else None
        ema100 = latest['ema100'] if 'ema100' in latest else None
        ema200 = latest['ema200'] if 'ema200' in latest else None
        rsi = latest['rsi14']
        atr = latest['atr14']
        
        # Recent price action (last 5 days)
        recent_data = df.tail(5)[['close', 'R1', 'R2', 'R3', 'rsi14', 'atr14']].round(2)
        # Add date column for template display
        recent_data_with_dates = recent_data.copy()
        recent_data_with_dates['date'] = recent_data.index.strftime('%Y-%m-%d')
        
        stock_data = {
            'symbol': symbol,
            'current_price': current_price,
            'levels': {
                'p': latest['P'],
                'r1': r1_level,
                'r2': r2_level,
                'r3': r3_level,
                's1': s1_level,
                's2': s2_level,
                's3': s3_level,
                'ema5': ema5,
                'ema10': ema10,
                'ema20': ema20,
                'ema50': ema50,
                'ema100': ema100,
                'ema200': ema200
            },
            'indicators': {
                'rsi': rsi,
                'atr': atr
            },
            'breakout_signal': breakout_signal,
            'resistance_retest_signal': resistance_retest_signal,
            'pullback_signal': pullback_signal,
            'backtest': backtest_results,
            'recent_data': recent_data_with_dates.to_dict('records'),
            'recent_data_html': recent_data.to_html(classes='table table-sm table-striped'),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return render_template('stock_detail.html', stock=stock_data)
        
    except Exception as e:
        return f"<h1>Error</h1><p>Error loading data for {symbol}: {str(e)}</p>", 500

@app.route('/health')
def health():
    """Health check endpoint for Cloud Run"""
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}, 200

if __name__ == '__main__':
    # Respect environment variables for deployment platforms like Railway
    port = int(os.environ.get('PORT', 5001))
    # Use the FLASK_DEBUG from .env file, with fallback to environment
    debug_mode = FLASK_DEBUG if 'FLASK_DEBUG' in os.environ else os.environ.get('FLASK_DEBUG', '1') in ('1', 'true', 'True')
    
    print(f"🚀 Starting Flask app with debug={debug_mode}, port={port}")
    print(f"⚙️ Cache config: {cache_refresh_minutes}min refresh, {trading_start_hour}:00-{trading_end_hour}:00")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)