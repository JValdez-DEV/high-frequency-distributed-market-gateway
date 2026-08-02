#!/usr/bin/env python3
import os
import glob
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from crypto_sweep_engine import backtest_crypto_sweep_trades, CryptoSweepConfig
from env_config import BASE_DIR, get_env, get_path

# --- ENVIRONMENT & SECURE CREDENTIAL LOADING ---
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

API_KEY = get_env("ALPACA_API_KEY")
SECRET_KEY = get_env("ALPACA_API_SECRET")

if not API_KEY or not SECRET_KEY:
    print(f"\n[CRITICAL ERROR] Failed to load credentials from: {ENV_PATH}")
    raise SystemExit(1)

DATA_DIR = get_path(get_env('DATA_DIR', default='massive_data'))
LOOKBACK_DAYS = 180

NEW_CRYPTO_TARGETS = {
    "LTC/USD": "X_LTCUSD_1m_master.csv",
    "LINK/USD": "X_LINKUSD_1m_master.csv",
    "DOGE/USD": "X_DOGEUSD_1m_master.csv",
    "AVAX/USD": "X_AVAXUSD_1m_master.csv"
}

def ingest_expansion_cryptos():
    client = CryptoHistoricalDataClient(API_KEY, SECRET_KEY)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)

    print(f"\n{'='*90}\nALPACA CRYPTO INGESTION - SECURE EXPANSION MATRIX\n{'='*90}", flush=True)
    
    for symbol, filename in NEW_CRYPTO_TARGETS.items():
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(file_path):
            print(f"[-] {filename} already exists. Skipping network stream.", flush=True)
            continue
            
        print(f"[-] Streaming 180-day data via Secure .env Credentials for {symbol}...", flush=True)
        request_params = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,
            start=start_date,
            end=end_date
        )
        
        try:
            bars = client.get_crypto_bars(request_params)
            df = bars.df
            if df.empty:
                print(f"  -> Warning: No data returned for {symbol}", flush=True)
                continue
            
            df = df.reset_index()
            if "symbol" in df.columns:
                df = df[df["symbol"] == symbol]
            
            df = df.rename(columns={
                "timestamp": "Time", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
            })
            df = df.set_index("Time")
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df.to_csv(file_path)
            print(f"  -> SUCCESS: Saved {len(df):,} candles to {file_path}", flush=True)
        except Exception as e:
            print(f"  -> Ingestion Error for {symbol}: {e}", flush=True)

def run_grid_optimization():
    print(f"\n{'=' * 90}\nCRYPTO SWEEP PARAMETER HYPER-TUNING MATRIX\n{'=' * 90}", flush=True)
    print(f"{'TICKER':<10} | {'VOL M':<5} | {'R:R':<4} | {'BUF%':<5} | {'TRADES':<6} | {'WIN%':<7} | {'NET PNL'}", flush=True)
    print("-" * 90, flush=True)

    all_crypto_files = sorted(glob.glob(os.path.join(DATA_DIR, "X_*_1m_master.csv")))
    optimization_matrix = []

    for file_path in all_crypto_files:
        filename = os.path.basename(file_path)
        ticker = filename.split("_1m_master")[0]
        
        # Real-time heartbeat indicator
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing hyper-tuning matrices for {ticker}...", end="", flush=True)

        try:
            raw_df = pd.read_csv(file_path)
            for col in raw_df.columns:
                if col.lower() in ["time", "timestamp", "date"]:
                    raw_df = raw_df.rename(columns={col: "time"})
                    break

            best_r = -float('inf')
            best_cfg = None
            best_stats = None

            for vol_mult in [1.5, 2.0]:
                for rr in [1.5, 2.0, 3.0]:
                    for buffer in [0.005, 0.01]:
                        config = CryptoSweepConfig(
                            volume_multiplier=vol_mult,
                            reward_risk=rr,
                            stop_wick_buffer_pct=buffer
                        )
                        _, results = backtest_crypto_sweep_trades(raw_df, config)
                        if results.empty:
                            continue

                        total_trades = len(results)
                        wins = len(results[results["exit_reason"] == "take_profit"])
                        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
                        total_r = results["r_multiple"].sum()

                        if total_r > best_r:
                            best_r = total_r
                            best_cfg = (vol_mult, rr, buffer)
                            best_stats = (total_trades, win_rate, total_r)

            # Clear line and overwrite with structured formatting instantly
            print("\r", end="", flush=True)
            if best_cfg:
                vm, r_r, buf = best_cfg
                t_count, w_r, net_r = best_stats
                print(f"{ticker:<10} | {vm:<5.1f} | {r_r:<4.1f} | {buf*100:<4.1f}% | {t_count:<6} | {w_r:>5.2f}% | {net_r:+.2f}R", flush=True)
                optimization_matrix.append({
                    "ticker": ticker, "vol_mult": vm, "rr": r_r, "buffer": buf, "trades": t_count, "win_rate": w_r, "net_r": net_r
                })
            else:
                print(f"{ticker:<10} | No viable configurations found.", flush=True)

        except Exception as e:
            print(f"\r{ticker:<10} | Optimization Failure: {e}", flush=True)
            
    print(f"\n{'=' * 90}\nPRODUCTION SELECTION RECOMMENDATION\n{'=' * 90}", flush=True)
    for item in optimization_matrix:
        if item["net_r"] >= 10.0 and item["trades"] >= 30:
            status = "DEPLOY TO LIVE PAPER TEST"
        elif item["net_r"] > 0:
            status = "MONITOR / INSUFFICIENT EDGE"
        else:
            status = "BLACKLIST FROM DEPLOYMENT"
        print(f"Asset: {item['ticker']:<10} | Top Cfg: [VolM: {item['vol_mult']}, RR: {item['rr']}, Buf: {item['buffer']*100}%] -> {status}", flush=True)

if __name__ == "__main__":
    ingest_expansion_cryptos()
    run_grid_optimization()
