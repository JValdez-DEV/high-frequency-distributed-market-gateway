import os
import time
import json
from datetime import datetime, timedelta
import ccxt
import pandas as pd
from dotenv import load_dotenv

# =====================================================================
# SYSTEM INITIALIZATION
# =====================================================================
load_dotenv()

SYMBOL = 'BTC/USDT'
TIMEFRAME = '5m'
LEDGER_FILE = 'virtual_ledger.json'

# --- THE AGGRESSIVE BARBARIAN PARAMETERS ---
TRAP_ZONE = 0.005
RSI_MIN = 35
RSI_MAX = 65
RISK_PCT = 0.02
REWARD_RATIO = 3

# --- THE GLOBAL KILL SWITCH ---
STARTING_CAPITAL = 1000.00
DRAWDOWN_LIMIT_PCT = 0.15 # 15%
CAPITAL_FLOOR = STARTING_CAPITAL * (1 - DRAWDOWN_LIMIT_PCT) # $850.00

exchange = ccxt.kraken({'enableRateLimit': True})

# =====================================================================
# THE LEDGER AGENT (VIRTUAL ACCOUNTING + GLOBAL KILL SWITCH)
# =====================================================================
class LedgerAgent:
    def __init__(self):
        if os.path.exists(LEDGER_FILE):
            with open(LEDGER_FILE, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {
                "balance": STARTING_CAPITAL,
                "open_trade": None,
                "consecutive_losses": 0,
                "lockout_until": None,
                "permanent_kill": False,
                "history": []
            }
        self.save()

    def save(self):
        with open(LEDGER_FILE, 'w') as f:
            json.dump(self.data, f, indent=4)

    def status_check(self):
        """Checks for both Cooldowns and Permanent Kill Switches."""
        if self.data["balance"] <= CAPITAL_FLOOR:
            self.data["permanent_kill"] = True
            self.save()
            return "KILLED"

        if self.data["lockout_until"]:
            lock_time = datetime.fromisoformat(self.data["lockout_until"])
            if datetime.now() < lock_time:
                return "COOLDOWN"
            else:
                self.data["lockout_until"] = None
                self.data["consecutive_losses"] = 0
                self.save()
        
        return "ACTIVE"

# =====================================================================
# THE MASTER HUNTER V2.1
# =====================================================================
def run_hunter():
    print(f"\n\033[97m=== PROJECT TRADE HUNTER V2.1 (15% LIMIT ACTIVE) ===\033[0m")
    print(f"Target: {SYMBOL} | Floor: ${CAPITAL_FLOOR:.2f}\n")
    ledger = LedgerAgent()
    
    while True:
        try:
            status = ledger.status_check()
            
            if status == "KILLED":
                print(f"\033[91m[!!!] GLOBAL KILL SWITCH TRIGGERED: Balance below ${CAPITAL_FLOOR:.2f}. System offline.\033[0m")
                break 
                
            if status == "COOLDOWN":
                print(f"[{datetime.now()}] 24H Cooldown active (3 Consecutive Losses).")
                time.sleep(600)
                continue

            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA_Vol_20'] = df['volume'].rolling(window=20).mean()
            delta = df['close'].diff()
            up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (ema_up / ema_down)))
            
            curr = df.iloc[-1]
            price = curr['close']

            if ledger.data["open_trade"]:
                trade = ledger.data["open_trade"]
                print(f"[{datetime.now()}] MONITORING: Entry ${trade['entry']:.2f} | SL ${trade['sl']:.2f} | TP ${trade['tp']:.2f}")
                
                if curr['low'] <= trade['sl']:
                    ledger.data["balance"] -= trade['risk_usd']
                    ledger.data["consecutive_losses"] += 1
                    print(f"\033[91m[VIRTUAL LOSS] New Balance: ${ledger.data['balance']:.2f}\033[0m")
                    if ledger.data["consecutive_losses"] >= 3:
                        ledger.data["lockout_until"] = (datetime.now() + timedelta(hours=24)).isoformat()
                    ledger.data["open_trade"] = None
                    ledger.save()
                    
                elif curr['high'] >= trade['tp']:
                    profit = trade['risk_usd'] * REWARD_RATIO
                    ledger.data["balance"] += profit
                    ledger.data["consecutive_losses"] = 0
                    print(f"\033[92m[VIRTUAL WIN] New Balance: ${ledger.data['balance']:.2f}\033[0m")
                    ledger.data["open_trade"] = None
                    ledger.save()
            
            else:
                diff = abs(price - curr['MA20']) / curr['MA20']
                print(f"[{datetime.now()}] Sentinel: BTC @ ${price:.2f} | Diff: {diff*100:.3f}% | RSI: {curr['RSI']:.2f}")
                
                if diff <= TRAP_ZONE:
                    if curr['volume'] > curr['MA_Vol_20'] and RSI_MIN <= curr['RSI'] <= RSI_MAX:
                        risk_usd = ledger.data["balance"] * RISK_PCT
                        sl_dist = (risk_usd / ledger.data["balance"]) * price
                        
                        ledger.data["open_trade"] = {
                            "entry": price,
                            "sl": price - sl_dist,
                            "tp": price + (sl_dist * REWARD_RATIO),
                            "risk_usd": risk_usd
                        }
                        print(f"\033[94m[PAPER TRADE OPENED] Target: ${ledger.data['open_trade']['tp']:.2f}\033[0m")
                        ledger.save()

            time.sleep(300) 

        except Exception as e:
            print(f"Runtime Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_hunter()
