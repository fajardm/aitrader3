import optuna
import json
import pandas as pd
from backtesting import Backtest
from backtest import Breakout, Pullback, ResistanceRetest, parse_args, PARAMS_DIR
from fetch_data import load_ohlcv
from indicators import calculate_indicators

def objective(trial: optuna.Trial, df: pd.DataFrame, cash: float, strategy: str = "breakout") -> float:
    strategy_cls = None
    params = {}

    if strategy == "breakout":
        strategy_cls = Breakout
        params = {
            "n_sl_r1": trial.suggest_float("n_sl_r1", 0.3, 1.0, step=0.1),
            "n_tp_r1": trial.suggest_float("n_tp_r1", 0.8, 1.8, step=0.1),
            "n_days_r1": trial.suggest_int("n_days_r1", 1, 6),
            "n_rsi14_r1": trial.suggest_int("n_rsi14_r1", 30, 45),

            "n_sl_r2": trial.suggest_float("n_sl_r2", 0.8, 1.6, step=0.1),
            "n_tp_r2": trial.suggest_float("n_tp_r2", 1.6, 3.0, step=0.1),
            "n_days_r2": trial.suggest_int("n_days_r2", 3, 10),
            "n_rsi14_r2": trial.suggest_int("n_rsi14_r2", 35, 55),

            "n_sl_r3": trial.suggest_float("n_sl_r3", 1.0, 2.0, step=0.1),
            "n_tp_r3": trial.suggest_float("n_tp_r3", 2.0, 4.0, step=0.1),
            "n_days_r3": trial.suggest_int("n_days_r3", 5, 15),
            "n_rsi14_r3": trial.suggest_int("n_rsi14_r3", 35, 60),
        }
    elif strategy == "pullback":
        strategy_cls = Pullback
        params = {
            "n_sl_s1": trial.suggest_float("n_sl_s1", 0.4, 1.2),
            "n_tp_s1": trial.suggest_float("n_tp_s1", 1.0, 2.6),
            "n_days_s1": trial.suggest_int("n_days_s1", 2, 8, step=1),

            "n_sl_s2": trial.suggest_float("n_sl_s2", 0.8, 1.6),
            "n_tp_s2": trial.suggest_float("n_tp_s2", 1.6, 3.0),
            "n_days_s2": trial.suggest_int("n_days_s2", 4, 10, step=1),

            "n_sl_s3": trial.suggest_float("n_sl_s3", 1.2, 2.0),
            "n_tp_s3": trial.suggest_float("n_tp_s3", 2.0, 4.0),
            "n_days_s3": trial.suggest_int("n_days_s3", 6, 14, step=1),

            "n_high_fac_s1": trial.suggest_float("n_high_fac_s1", 0.985, 0.995),
            "n_low_fac_s1": trial.suggest_float("n_low_fac_s1", 1.005, 1.02),
            "n_high_fac_s2": trial.suggest_float("n_high_fac_s2", 0.975, 0.99),
            "n_low_fac_s2": trial.suggest_float("n_low_fac_s2", 1.01, 1.03),
            "n_high_fac_s3": trial.suggest_float("n_high_fac_s3", 0.96, 0.985),
            "n_low_fac_s3": trial.suggest_float("n_low_fac_s3", 1.02, 1.05),
        }
    elif strategy == "resistance_retest":
        strategy_cls = ResistanceRetest
        params = {
            "n_sl_r1": trial.suggest_float("n_sl_r1", 0.6, 1.6),
            "n_tp_r1": trial.suggest_float("n_tp_r1", 1.2, 3.0),
            "n_days_r1": trial.suggest_int("n_days_r1", 3, 10, step=1),

            "n_sl_r2": trial.suggest_float("n_sl_r2", 1.0, 2.2),
            "n_tp_r2": trial.suggest_float("n_tp_r2", 1.8, 3.6),
            "n_days_r2": trial.suggest_int("n_days_r2", 4, 12, step=1),

            "n_sl_r3": trial.suggest_float("n_sl_r3", 1.6, 3.0),
            "n_tp_r3": trial.suggest_float("n_tp_r3", 2.5, 4.5),
            "n_days_r3": trial.suggest_int("n_days_r3", 6, 14, step=1),

            "n_high_fac_r1": trial.suggest_float("n_high_fac_r1", 0.985, 1.005),
            "n_low_fac_r1": trial.suggest_float("n_low_fac_r1", 0.995, 1.03),
            "n_high_fac_r2": trial.suggest_float("n_high_fac_r2", 0.97, 0.995),
            "n_low_fac_r2": trial.suggest_float("n_low_fac_r2", 1.01, 1.04),
            "n_high_fac_r3": trial.suggest_float("n_high_fac_r3", 0.96, 0.99),
            "n_low_fac_r3": trial.suggest_float("n_low_fac_r3", 1.02, 1.06),

            "n_rsi14": trial.suggest_int("n_rsi14", 60, 80)
        }

    for k, v in params.items():
        setattr(strategy_cls, k, v)

    # run backtest
    bt = Backtest(df, strategy_cls, cash=cash, exclusive_orders=True, trade_on_close=False)
    res = bt.run()

    return_pct = float(res['Return [%]'])
    win_rate_pct = float(res['Win Rate [%]'])
    max_dd_pct = float(res['Max. Drawdown [%]'])
    metric = return_pct + win_rate_pct * 0 - abs(max_dd_pct) * 0

    return metric

def main():
    args = parse_args()
    # Load data and calculate indicators
    df = load_ohlcv(args.symbol, start_date=args.start_date, end_date=args.end_date)
    df = calculate_indicators(df)
    
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=200))
    study.optimize(lambda trial: objective(trial, df, args.cash, args.strategy), n_trials=1000, n_jobs=10)

    print("Best trial:")
    print(study.best_trial.params)
    print("Best value:", study.best_value)
    params = study.best_trial.params

    # save to JSON
    file_name = f"{args.symbol.replace('.JK', '')}_{args.strategy}.json"
    path = PARAMS_DIR/ file_name
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(params, fp, indent=2)

    print(f"Saved best params to {path}")

if __name__ == "__main__":
    main()