import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import time

# =====================================================================
# AGGRESSIVE BACKTEST PARAMETERS (V4)
# =====================================================================
SYMBOL = 'BTC/USDT'
TIMEFRAME = '5m'
DAYS_BACK = 30    # 30-day stress test
STARTING_BALANCE = 1000.00
RISK_PCT = 0.02 
REWARD_RATIO = 3
TRAP_ZONE = 0.005 # Increased to 0.5% for more frequency
RSI_MIN = 35      # Loosened from 40
RSI_MAX = 65      # Loosened from 60

data_exchange = ccxt.coinbaseexchange({'enableRateLimit': True})

def fetch_historical_data():
    print(f"[*] AGGRESSIVE TEST: Fetching {DAYS_BACK} days from Coinbase...")
    since = data_exchange.milliseconds() - (DAYS_BACK * 24 * 60 * 60 * 1000)
    all_ohlcv = []
    
    while since < data_exchange.milliseconds():
        try:
            ohlcv = data_exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since)
            if not ohlcv: break
            since = ohlcv[-1][0] + 1
            all_ohlcv.extend(ohlcv)
            if len(ohlcv) < 10: break
            time.sleep(0.1)
        except Exception as e:
            print(f"Fetch error: {e}")
            break

    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.drop_duplicates(subset=['timestamp'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"[*] TOTAL DATA LOADED: {len(df)} candles.\n")
    return df

def apply_indicators(df):
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA_Volume_20'] = df['volume'].rolling(window=20).mean()
    delta = df['close'].diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + (ema_up / ema_down)))
    return df

def run_backtest(df):
    balance = STARTING_BALANCE
    open_trade = None
    trades_taken, wins, losses = 0, 0, 0

    for index, row in df.iterrows():
        if pd.isna(row['MA20']): continue

        if open_trade:
            if row['low'] <= open_trade['sl_price']:
                balance -= open_trade['risk_usd']
                losses += 1
                open_trade = None
            elif row['high'] >= open_trade['tp_price']:
                balance += (open_trade['risk_usd'] * REWARD_RATIO)
                wins += 1
                open_trade = None
            continue

        # Aggressive Strategy Logic
        diff = abs(row['close'] - row['MA20']) / row['MA20']
        if diff <= TRAP_ZONE:
            if row['volume'] > row['MA_Volume_20'] and RSI_MIN <= row['RSI'] <= RSI_MAX:
                trades_taken += 1
                risk_usd = balance * RISK_PCT
                sl_dist = (risk_usd / balance) * row['close']
                
                open_trade = {
                    'entry_price': row['close'],
                    'sl_price': row['close'] - sl_dist,
                    'tp_price': row['close'] + (sl_dist * REWARD_RATIO),
                    'risk_usd': risk_usd
                }

    net_profit = balance - STARTING_BALANCE
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    
    print("\n" + "="*40)
    print("\033[91m=== AGGRESSIVE BARBARIAN RESULTS ===\033[0m")
    print(f"Window:           {DAYS_BACK} Days")
    print(f"Starting Capital: ${STARTING_BALANCE:,.2f}")
    print(f"Ending Capital:   ${balance:,.2f}")
    print(f"Net PnL:          \033[{'92m+' if net_profit >= 0 else '91m'}${net_profit:,.2f}\033[0m")
    print("-" * 40)
    print(f"Total Trades:     {trades_taken}")
    print(f"Wins:             {wins}")
    print(f"Losses:           {losses}")
    print(f"Win Rate:         {win_rate:.2f}%")
    print("="*40 + "\n")

if __name__ == "__main__":
    data = fetch_historical_data()
    if len(data) > 100:
        data = apply_indicators(data)
        run_backtest(data)
