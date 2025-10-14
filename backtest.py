import argparse
import json
import datetime as dt
from typing import Dict, Tuple
from pathlib import Path
from backtesting import Backtest, Strategy
from fetch_data import load_ohlcv
from indicators import calculate_indicators

PARAMS_DIR = Path(__file__).parent / "params"
PARAMS_DIR.mkdir(exist_ok=True)

class Breakout(Strategy):
    n_sl_r1 = 0.6
    n_tp_r1 = 1.2
    n_days_r1 = 3
    n_rsi14_r1 = 50
    n_sl_r2 = 1.0
    n_tp_r2 = 2.0
    n_days_r2 = 6
    n_rsi14_r2 = 55
    n_sl_r3 = 1.2
    n_tp_r3 = 2.5
    n_days_r3 = 8
    n_rsi14_r3 = 60
    n_vol = 1.2

    def init(self):
        print("Initializing Breakout strategy...")
        self.stop_loss = None
        self.take_profit = None
        self.max_days = None
        self.days_in_trade = 0

    def next(self):
        in_position = bool(self.position)

        if not in_position:
            if self.has_signal():
                self.buy(sl=self.stop_loss, tp=self.take_profit)
                self.days_in_trade = 0
        else:
            self.days_in_trade += 1
            if self.days_in_trade >= self.max_days:
                self.position.close()
                self.days_in_trade = 0

    def has_signal(self) -> bool:
        conditions = self.get_conditions()
        has_signal = any(conditions.values())

        if has_signal:
            level = self.get_level(conditions)
            atr = self.data.atr14[-1]
            params = self.get_params(level, atr)

            # ensure sl/tp are scalars (floats)
            self.stop_loss = float(params['stop_loss'])
            self.take_profit = float(params['take_profit'])
            self.max_days = int(params['max_days'])

        return has_signal

    def get_conditions(self) -> Dict[str, bool]:
        # read only current bar values (scalars)
        close = float(self.data.Close[-1])
        prev_close = float(self.data.Close[-2])
        open = float(self.data.Open[-1])
        high = float(self.data.High[-1])
        r1 = float(self.data.r1[-1])
        r2 = float(self.data.r2[-1])
        r3 = float(self.data.r3[-1])
        rsi14 = float(self.data.rsi14[-1])
        ema10 = float(self.data.ema10[-1])
        ema20 = float(self.data.ema20[-1])

        # optional volume confirmation (if Volume column exists)
        vol_ok = True
        try:
            vol = float(self.data.Volume[-1])
            vol_sma20 = float(self.data.Volume[-20:].mean())
            vol_ok = vol > vol_sma20 * self.n_vol
        except Exception:
            # volume not available or not enough history -> skip volume check
            vol_ok = True

        return {
            'r1_breakout': (
                (close > r1) and
                (prev_close <= r1) and
                # (high > r1) and
                (rsi14 > self.n_rsi14_r1) and
                (close > ema10) and
                (close > open) and
                vol_ok
            ),
            'r2_breakout': (
                (close > r2) and
                (prev_close <= r2) and
                # (high > r2) and
                (rsi14 > self.n_rsi14_r2) and
                (close > ema20) and
                vol_ok
            ),
            'r3_breakout': (
                (close > r3) and
                (prev_close <= r3) and
                # (high > r3) and
                (rsi14 > self.n_rsi14_r3) and
                (close > ema20) and
                vol_ok
            )
        }
    
    def get_level(self, breakout_status: Dict[str, bool]) -> str:
        if breakout_status['r3_breakout']:
            return 'r3'
        if breakout_status['r2_breakout']:
            return 'r2'
        return 'r1'

    def get_params(self, level: str, atr: float) -> Dict[str, float]:
        entry_price = float(self.data.Close[-1])

        if level == 'r1':
            return {
                'stop_loss': entry_price - self.n_sl_r1 * atr,
                'take_profit': entry_price + self.n_tp_r1 * atr,
                'max_days': self.n_days_r1
            }
        
        if level == 'r2':
            return {
                'stop_loss': entry_price - self.n_sl_r2 * atr,
                'take_profit': entry_price + self.n_tp_r2 * atr,
                'max_days': self.n_days_r2
            }
        
        return {
            'stop_loss': entry_price - self.n_sl_r3 * atr,
            'take_profit': entry_price + self.n_tp_r3 * atr,
            'max_days': self.n_days_r3
        }
    
class Pullback(Strategy):
    n_sl_s1 = 0.8
    n_tp_s1 = 1.8
    n_days_s1 = 5
    n_sl_s2 = 1.2
    n_tp_s2 = 2.2
    n_days_s2 = 7
    n_sl_s3 = 1.5
    n_tp_s3 = 2.8
    n_days_s3 = 10
    n_rsi14_s1 = 70
    n_rsi14_s2 = 65
    n_rsi14_s3 = 60
    n_vol = 1.2

    def init(self):
        print("Initializing Pullback strategy...")
        self.stop_loss = None
        self.take_profit = None
        self.max_days = None
        self.entry_price = None
        self.days_in_trade = 0

    def next(self):
        in_position = bool(self.position)

        if not in_position:
            if self.has_signal():
                print(f"Date {self.data.index[-1]} Entering trade at {self.entry_price} with SL {self.stop_loss} and TP {self.take_profit}")
                self.buy(limit=self.entry_price, sl=self.stop_loss, tp=self.take_profit)
                self.days_in_trade = 0
        else:
            self.days_in_trade += 1
            if self.days_in_trade >= self.max_days:
                self.position.close()
                self.days_in_trade = 0

    def has_signal(self) -> bool:
        conditions = self.get_conditions()
        has_signal = any(conditions.values())

        if has_signal:
            level = self.get_level(conditions)
            atr = self.data.atr14[-1]
            params = self.get_params(level, atr)
            
            # ensure sl/tp are scalars (floats)
            self.stop_loss = float(params['stop_loss'])
            self.take_profit = float(params['take_profit'])
            self.max_days = int(params['max_days'])
            self.entry_price = float(params['entry_price'])

        return has_signal

    def get_conditions(self) -> Dict[str, bool]:
        open = float(self.data.Open[-1])
        high = float(self.data.High[-1])
        low = float(self.data.Low[-1])
        close = float(self.data.Close[-1])
        prev_close = float(self.data.Close[-2])
        s1 = float(self.data.s1[-1])
        s2 = float(self.data.s2[-1])
        s3 = float(self.data.s3[-1])
        rsi14 = float(self.data.rsi14[-1])
        ema10 = float(self.data.ema10[-1])
        ema20 = float(self.data.ema20[-1])

        # tolerances (adjustable)
        touch_tol = 0.05      # allowed % above/below support to count as "touched" (1%)
        max_breach = 0.09     # maximum allowed breach below support (2%)

        # optional volume confirmation (if Volume column exists)
        vol_ok = True
        try:
            vol = float(self.data.Volume[-1])
            vol_sma20 = float(self.data.Volume[-20:].mean())
            vol_ok = vol > vol_sma20 * self.n_vol
        except Exception:
            vol_ok = True

        # helper: check a "clean" touch of support coming from above
        def touched_support(level: float) -> bool:
            upper = level * (1.0 + touch_tol)
            lower = level * (1.0 - max_breach)
            return (prev_close > level) and (low <= upper) and (low >= lower)
        
        # helper: bullish rejection candle (close in upper part of range)
        def bullish_rejection() -> bool:
            range_ = high - low if high > low else 1e-6
            # close within top 30% of the bar and a bullish candle
            return (close > open) and ((high - close) <= 0.3 * range_)

        return {
            's1_pullback': (
                touched_support(s1) and
                (close > s1) and
                (close > ema20) and
                bullish_rejection() and
                (rsi14 < self.n_rsi14_s1) and
                vol_ok
            ),
            's2_pullback': (
                touched_support(s2) and
                (close > s2) and
                (close > ema20) and
                bullish_rejection() and
                (rsi14 < self.n_rsi14_s2) and
                vol_ok
            ),
            's3_pullback': (
                touched_support(s3) and
                (close > s3) and
                (close > ema10) and    # allow shorter-term trend for deeper support
                bullish_rejection() and
                (rsi14 < self.n_rsi14_s3) and
                vol_ok
            )
        }
    
    def get_level(self, pullback_status: Dict[str, bool]) -> str:
        if pullback_status['s1_pullback']:
            return 's1'
        if pullback_status['s2_pullback']:
            return 's2'
        return 's3'

    def get_params(self, level: str, atr: float) -> Dict[str, float]:
        s1 = float(self.data.s1[-1])
        s2 = float(self.data.s2[-1])
        s3 = float(self.data.s3[-1])

        if level == 's1':
            return {
                'stop_loss': s1 - self.n_sl_s1 * atr,
                'take_profit': s1 + self.n_tp_s1 * atr,
                'max_days': self.n_days_s1,
                'entry_price': s1
            }
        
        if level == 's2':
            return {
                'stop_loss': s2 - self.n_sl_s2 * atr,
                'take_profit': s2 + self.n_tp_s2 * atr,
                'max_days': self.n_days_s2,
                'entry_price': s2
            }
        
        return {
            'stop_loss': s3 - self.n_sl_s3 * atr,
            'take_profit': s3 + self.n_tp_s3 * atr,
            'max_days': self.n_days_s3,
            'entry_price': s3
        }

class ResistanceRetest(Strategy):
    n_sl_r1 = 1.0
    n_tp_r1 = 2.0
    n_days_r1 = 6
    n_sl_r2 = 1.5
    n_tp_r2 = 2.5
    n_days_r2 = 8
    n_sl_r3 = 2.0
    n_tp_r3 = 3.0
    n_days_r3 = 10
    n_high_fac_r1 = 0.99
    n_low_fac_r1 = 1.01
    n_high_fac_r2 = 0.98
    n_low_fac_r2 = 1.02
    n_high_fac_r3 = 0.97
    n_low_fac_r3 = 1.03
    n_rsi14 = 70

    def init(self):
        print("Initializing ResistanceRetest strategy...")
        self.stop_loss = None
        self.take_profit = None
        self.max_days = None
        self.entry_price = None
        self.days_in_trade = 0

    def next(self):
        in_position = bool(self.position)

        if not in_position:
            if self.has_signal():
                self.buy(limit=self.entry_price, sl=self.stop_loss, tp=self.take_profit)
                self.days_in_trade = 0
        else:
            self.days_in_trade += 1
            if self.days_in_trade >= self.max_days:
                self.position.close()
                self.days_in_trade = 0

    def has_signal(self) -> bool:
        conditions = self.get_conditions()
        has_signal = any(conditions.values())

        if has_signal:
            level = self.get_level(conditions)
            atr = self.data.atr14[-1]
            params = self.get_params(level, atr)

            # ensure sl/tp are scalars (floats)
            self.stop_loss = float(params['stop_loss'])
            self.take_profit = float(params['take_profit'])
            self.max_days = int(params['max_days'])
            self.entry_price = float(params['entry_price'])

        return has_signal

    def get_conditions(self) -> Dict[str, bool]:
        # read only current bar values (scalars)
        close = float(self.data.Close[-1])
        low = float(self.data.Low[-1])
        high = float(self.data.High[-1])
        r1 = float(self.data.r1[-1])
        r2 = float(self.data.r2[-1])
        r3 = float(self.data.r3[-1])
        ema20 = float(self.data.ema20[-1])
        rsi14 = float(self.data.rsi14[-1])

        return {
            'r1_triggered': (
                (low <= r1 * self.n_low_fac_r1) and
                (high >= r1 * self.n_high_fac_r1) and
                (close > r1) and
                (close > ema20) and
                (rsi14 < self.n_rsi14)
            ),
            'r2_triggered': (
                (low <= r2 * self.n_low_fac_r2) and
                (high >= r2 * self.n_high_fac_r2) and
                (close > r2) and
                (close > ema20) and
                (rsi14 < self.n_rsi14)
            ),
            'r3_triggered': (
                (low <= r3 * self.n_low_fac_r3) and
                (high >= r3 * self.n_high_fac_r3) and
                (close > r3) and
                (close > ema20) and
                (rsi14 < self.n_rsi14)
            )
        }
    
    def get_level(self, conditions: Dict[str, bool]) -> str:
        if conditions['r3_triggered']:
            return 'r3'
        if conditions['r2_triggered']:
            return 'r2'
        return 'r1'

    def get_params(self, level: str, atr: float) -> Dict[str, float]:
        r1 = float(self.data.r1[-1])
        r2 = float(self.data.r2[-1])
        r3 = float(self.data.r3[-1])

        if level == 'r1':
            return {
                'stop_loss': r1 - self.n_sl_r1 * atr,
                'take_profit': r1 + self.n_tp_r1 * atr,
                'max_days': self.n_days_r1,
                'entry_price': r1
            }
        
        if level == 'r2':
            return {
                'stop_loss': r2 - self.n_sl_r2 * atr,
                'take_profit': r2 + self.n_tp_r2 * atr,
                'max_days': self.n_days_r2,
                'entry_price': r2
            }
        
        return {
            'stop_loss': r3 - self.n_sl_r3 * atr,
            'take_profit': r3 + self.n_tp_r3 * atr,
            'max_days': self.n_days_r3,
            'entry_price': r3
        }

def run(symbol: str, cash: float, start_date: str, end_date: str, strategy: str) -> Tuple[Backtest, Dict]:
    # Load data and calculate indicators
    df = load_ohlcv(symbol, start_date=start_date, end_date=end_date)
    df = calculate_indicators(df)

    print(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    params_file = f"{symbol.replace('.JK', '')}_{strategy}.json"
    path = PARAMS_DIR / params_file

    strategy_cls = None

    # Load best-params JSON if present and apply to Breakout class
    try:
        with open(path, "r", encoding="utf-8") as f:
            best = json.load(f)

        if strategy == "breakout":
            strategy_cls = Breakout
            # Override Breakout class attributes if present in JSON
            strategy_cls.n_sl_r1 = float(best.get("n_sl_r1", Breakout.n_sl_r1))
            strategy_cls.n_sl_r2 = float(best.get("n_sl_r2", Breakout.n_sl_r2))
            strategy_cls.n_sl_r3 = float(best.get("n_sl_r3", Breakout.n_sl_r3))
            strategy_cls.n_tp_r1 = float(best.get("n_tp_r1", Breakout.n_tp_r1))
            strategy_cls.n_tp_r2 = float(best.get("n_tp_r2", Breakout.n_tp_r2))
            strategy_cls.n_tp_r3 = float(best.get("n_tp_r3", Breakout.n_tp_r3))
            strategy_cls.n_days_r1 = int(best.get("n_days_r1", Breakout.n_days_r1))
            strategy_cls.n_days_r2 = int(best.get("n_days_r2", Breakout.n_days_r2))
            strategy_cls.n_days_r3 = int(best.get("n_days_r3", Breakout.n_days_r3))
            strategy_cls.n_rsi14_r1 = int(best.get("n_rsi14_r1", Breakout.n_rsi14_r1))
            strategy_cls.n_rsi14_r2 = int(best.get("n_rsi14_r2", Breakout.n_rsi14_r2))
            strategy_cls.n_rsi14_r3 = int(best.get("n_rsi14_r3", Breakout.n_rsi14_r3))
        elif strategy == "pullback":
            strategy_cls = Pullback
            # strategy_cls.n_sl_s1 = float(best.get("n_sl_s1", Pullback.n_sl_s1))
            # strategy_cls.n_sl_s2 = float(best.get("n_sl_s2", Pullback.n_sl_s2))
            # strategy_cls.n_sl_s3 = float(best.get("n_sl_s3", Pullback.n_sl_s3))
            # strategy_cls.n_tp_s1 = float(best.get("n_tp_s1", Pullback.n_tp_s1))
            # strategy_cls.n_tp_s2 = float(best.get("n_tp_s2", Pullback.n_tp_s2))
            # strategy_cls.n_tp_s3 = float(best.get("n_tp_s3", Pullback.n_tp_s3))
            # strategy_cls.n_days_s1 = int(best.get("n_days_s1", Pullback.n_days_s1))
            # strategy_cls.n_days_s2 = int(best.get("n_days_s2", Pullback.n_days_s2))
            # strategy_cls.n_days_s3 = int(best.get("n_days_s3", Pullback.n_days_s3))
            # strategy_cls.n_high_fac_s1 = float(best.get("n_high_fac_s1", Pullback.n_high_fac_s1))
            # strategy_cls.n_high_fac_s2 = float(best.get("n_high_fac_s2", Pullback.n_high_fac_s2))
            # strategy_cls.n_high_fac_s3 = float(best.get("n_high_fac_s3", Pullback.n_high_fac_s3))
            # strategy_cls.n_low_fac_s1 = float(best.get("n_low_fac_s1", Pullback.n_low_fac_s1))
            # strategy_cls.n_low_fac_s2 = float(best.get("n_low_fac_s2", Pullback.n_low_fac_s2))
            # strategy_cls.n_low_fac_s3 = float(best.get("n_low_fac_s3", Pullback.n_low_fac_s3))
        elif strategy == "resistance_retest":
            strategy_cls = ResistanceRetest
            strategy_cls.n_sl_r1 = float(best.get("n_sl_r1", ResistanceRetest.n_sl_r1))
            strategy_cls.n_sl_r2 = float(best.get("n_sl_r2", ResistanceRetest.n_sl_r2))
            strategy_cls.n_sl_r3 = float(best.get("n_sl_r3", ResistanceRetest.n_sl_r3))
            strategy_cls.n_tp_r1 = float(best.get("n_tp_r1", ResistanceRetest.n_tp_r1))
            strategy_cls.n_tp_r2 = float(best.get("n_tp_r2", ResistanceRetest.n_tp_r2))
            strategy_cls.n_tp_r3 = float(best.get("n_tp_r3", ResistanceRetest.n_tp_r3))
            strategy_cls.n_days_r1 = int(best.get("n_days_r1", ResistanceRetest.n_days_r1))
            strategy_cls.n_days_r2 = int(best.get("n_days_r2", ResistanceRetest.n_days_r2))
            strategy_cls.n_days_r3 = int(best.get("n_days_r3", ResistanceRetest.n_days_r3))
            strategy_cls.n_high_fac_r1 = float(best.get("n_high_fac_r1", ResistanceRetest.n_high_fac_r1))
            strategy_cls.n_high_fac_r2 = float(best.get("n_high_fac_r2", ResistanceRetest.n_high_fac_r2))
            strategy_cls.n_high_fac_r3 = float(best.get("n_high_fac_r3", ResistanceRetest.n_high_fac_r3))
            strategy_cls.n_low_fac_r1 = float(best.get("n_low_fac_r1", ResistanceRetest.n_low_fac_r1))
            strategy_cls.n_low_fac_r2 = float(best.get("n_low_fac_r2", ResistanceRetest.n_low_fac_r2))
            strategy_cls.n_low_fac_r3 = float(best.get("n_low_fac_r3", ResistanceRetest.n_low_fac_r3))
            strategy_cls.n_rsi14 = int(best.get("n_rsi14", ResistanceRetest.n_rsi14))
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        print(f"Loaded {params_file} and applied to Breakout")
    except FileNotFoundError:
        print(f"{params_file} not found — using defaults")
    except Exception as e:
        print(f"Error loading {params_file}:", type(e).__name__, e)

    # Run backtest
    print(f"Running backtest with {strategy} strategy...")
    bt = Backtest(df,
                  strategy_cls,
                  cash=cash,
                  exclusive_orders=True,
                  trade_on_close=False)
    result = bt.run()

    return bt, result

def parse_args() -> argparse.Namespace:
    # Default values
    start_date = '2025-01-01'
    end_date = dt.datetime.now().strftime('%Y-%m-%d')

    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g., WIFI.JK)')
    parser.add_argument('--cash', type=float, default=1_000_000, help='Initial cash')
    parser.add_argument('--start-date', type=str, default=start_date, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=end_date, help='End date (YYYY-MM-DD)')
    parser.add_argument('--strategy', type=str, choices=['breakout', 'pullback', 'resistance_retest', 'xgboost'], default='breakout', help='Trading strategy to use')
    parser.add_argument('--plot', action='store_true', default=False, help='Show plot after backtest')
    return parser.parse_args()

def main():
    args = parse_args()
    # Run backtest
    bt, res = run(args.symbol, args.cash, args.start_date, args.end_date, args.strategy)
    if args.plot:
        bt.plot(plot_drawdown=True, plot_return=True, plot_equity=False)

    print(f"Backtest {args.strategy} run result summary:", res)

    trades = getattr(res, "_trades", None)
    if trades is not None:
        print("\n--- Trades ---")
        print(trades[
            ["EntryTime", "Size", "ExitTime", "EntryPrice", "ExitPrice",
             "SL", "TP", "PnL", "ReturnPct", "Duration"]
        ])

if __name__ == '__main__':
    main()
