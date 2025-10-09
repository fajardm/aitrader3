"""
Simple Flask Frontend for Trading Signals
=========================================

Flask web application with:
- /: List stocks with summary signals
- /stock/{symbol}: Detailed backtest and signal information
"""

from flask import Flask, render_template
import sys
import os
from datetime import datetime

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from live_signal import check_breakout_signal, check_resistance_retest_signal, check_pullback_signal
from fetch_data import load_ohlcv, clear_cache
from indicators import calculate_indicators
from realistic_backtest import run_realistic_backtest
from config import get_config

# Load configuration
config = get_config()
# Configure logging early
from config import configure_logging
configure_logging()
import logging

# Setup Flask app
app = Flask(__name__)
app.secret_key = config.secret_key

# Print configuration summary
config.print_config_summary()

@app.route('/')
def index():
    """Main page showing list of stocks with summary signals"""
    try:
        stocks_data = []
        
        for symbol in config.stock_symbols:
            try:
                # Get current data
                end_date = datetime.now().strftime('%Y-%m-%d')
                df = load_ohlcv(symbol, config.default_start_date, end_date)
                if df is None or len(df) < 50:
                    continue
                
                # Calculate indicators
                df = calculate_indicators(df)
                
                # Get live signals
                breakout_signal = check_breakout_signal(df, symbol, config.default_initial_cash)
                resistance_retest_signal = check_resistance_retest_signal(df, symbol, config.default_initial_cash)
                pullback_signal = check_pullback_signal(df, symbol, config.default_initial_cash)
                
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
                
            except (ValueError, OSError, KeyError) as e:
                print(f"Error processing {symbol}: {e}")
                continue
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate statistics
        total_stocks = len(stocks_data)
        total_buy = len([stock for stock in stocks_data if stock['overall_signal'] == 'BUY'])
        total_hold = len([stock for stock in stocks_data if stock['overall_signal'] == 'HOLD'])
        
        stats = {
            'total_stocks': total_stocks,
            'total_buy': total_buy,
            'total_hold': total_hold
        }
        
        return render_template('index.html', 
                             stocks=stocks_data, 
                             current_time=current_time,
                             stats=stats)

    except Exception as e:
        # Keep broad to surface unexpected runtime errors to the caller
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route('/stock/<symbol>')
def stock_detail(symbol):
    """Detailed view for a specific stock with backtest and signal information"""
    try:
        # Get current data
        end_date = datetime.now().strftime('%Y-%m-%d')
        df = load_ohlcv(symbol, config.default_start_date, end_date)
        if df is None or len(df) < 50:
            return f"<h1>Error</h1><p>Insufficient data for {symbol}</p>", 404
        
        last_date = df.index[-1].strftime('%Y-%m-%d')
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Get live signals with full details
        breakout_signal = check_breakout_signal(df, symbol, config.default_initial_cash)
        resistance_retest_signal = check_resistance_retest_signal(df, symbol, config.default_initial_cash)
        pullback_signal = check_pullback_signal(df, symbol, config.default_initial_cash)
        
        # Run backtest
        try:
            resistance_retest_final, resistance_retest_return, resistance_retest_dd, resistance_retest_sharpe = run_realistic_backtest(df, "Resistance_Retest", config.default_initial_cash)
            pullback_final, pullback_return, pullback_dd, pullback_sharpe = run_realistic_backtest(df, "Pullback", config.default_initial_cash)
            breakout_final, breakout_return, breakout_dd, breakout_sharpe = run_realistic_backtest(df, "Breakout", config.default_initial_cash)
            
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
            # Backtest may raise various runtime errors; keep broad but logged
            print(f"Backtest error for {symbol}: {e}")
            backtest_results = {
                'resistance_retest': {'total_return': 0, 'max_drawdown': 0, 'sharpe_ratio': 0, 'final_capital': config.default_initial_cash},
                'pullback': {'total_return': 0, 'max_drawdown': 0, 'sharpe_ratio': 0, 'final_capital': config.default_initial_cash},
                'breakout': {'total_return': 0, 'max_drawdown': 0, 'sharpe_ratio': 0, 'final_capital': config.default_initial_cash}
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
            'last_update': last_date,
            'start_date': config.default_start_date,
            'end_date': end_date
        }
        
        return render_template('stock_detail.html', stock=stock_data)
        
    except Exception as e:
        return f"<h1>Error</h1><p>Error loading data for {symbol}: {str(e)}</p>", 500

@app.route('/refetch-historical')
def refetch_historical():
    """Endpoint to refetch historical data for all stocks"""
    clear_cache()
    try:
        for symbol in config.stock_symbols:
            try:
                end_date = datetime.now().strftime('%Y-%m-%d')
                df = load_ohlcv(symbol, config.default_start_date, end_date)
                if df is None or len(df) < 1:
                    logging.warning("Insufficient data for %s during refetch.", symbol)
                    continue
                logging.info("Refetched historical data for %s, %d records.", symbol, len(df))
            except Exception as e:
                logging.error("Error refetching %s: %s", symbol, e)
                continue
        return "<h1>Refetch Completed</h1><p>Historical data refetch attempted for all symbols.</p>", 200
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route('/health')
def health():
    """Health check endpoint for Cloud Run"""
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}, 200

if __name__ == '__main__':
    # Use configuration from config class
    flask_config = config.get_flask_config()
    
    logging.info("🚀 Starting Flask app with debug=%s, port=%s", flask_config['debug'], flask_config['port'])
    
    app.run(debug=flask_config['debug'], host='0.0.0.0', port=flask_config['port'])