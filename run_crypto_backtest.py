#!/usr/bin/env python3
import os
import glob
import pandas as pd
from crypto_sweep_engine import backtest_crypto_sweep_trades, CryptoSweepConfig

# --- CONFIGURATION ---
from env_config import get_env, get_path

DATA_DIR = get_path(get_env('DATA_DIR', default='massive_data'))
CRYPTO_FILES = sorted(glob.glob(os.path.join(DATA_DIR, "X_*_1m_master.csv")))

def run_macro_sweep():
    print(f"\n{'=' * 90}\nCRYPTO LIQUIDITY SWEEP ENGINE - PERFORMANCE BACKTEST\n{'=' * 90}")
    print(f"{'TICKER':<10} | {'TRADES':<8} | {'W/L':<6} | {'WIN RATE':<10} | {'TOTAL PERFORMANCE'}")
    print("-" * 90)

    config = CryptoSweepConfig()

    for file_path in CRYPTO_FILES:
        filename = os.path.basename(file_path)
        ticker = filename.split("_1m_master")[0]

        if not os.path.exists(file_path):
            continue

        try:
            # Load raw data frame
            raw_df = pd.read_csv(file_path)
            
            # Explicitly force time column harmonization before engine ingestion
            for col in raw_df.columns:
                if col.lower() in ["time", "timestamp", "date"]:
                    raw_df = raw_df.rename(columns={col: "time"})
                    break

            # Execute bar-by-bar simulation
            trades, results = backtest_crypto_sweep_trades(raw_df, config)

            if results.empty:
                print(f"{ticker:<10} | {0:<8} | 0/0    | {0:>6.2f}% | 0.00R (No setups generated)")
                continue

            total_trades = len(results)
            wins = len(results[results["exit_reason"] == "take_profit"])
            losses = len(results[results["exit_reason"] == "stop_loss"])
            
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
            total_r = results["r_multiple"].sum()

            print(f"{ticker:<10} | {total_trades:<8} | {wins}/{losses:<4} | {win_rate:>6.2f}% | {total_r:+.2f}R Net Risk-Reward")

        except Exception as e:
            print(f"{ticker:<10} | ERROR during validation cycle: {e}")

if __name__ == "__main__":
    run_macro_sweep()
