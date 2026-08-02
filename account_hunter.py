import os, csv, pandas as pd
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
import requests

from env_config import BASE_DIR, get_env, get_path

load_dotenv(dotenv_path=BASE_DIR / '.env')
LOCAL_CRYPTO_START = 10000.00
LEDGER_FILE = get_path(get_env('LEDGER_FILE', default='trade_ledger.csv'))
ALPACA_API = tradeapi.REST(get_env('ALPACA_API_KEY'), get_env('ALPACA_API_SECRET'), get_env('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'), 'v2')

def audit_accounts():
    alpaca = ALPACA_API.get_account()
    crypto_cash = LOCAL_CRYPTO_START
    unrealized_pnl = 0.0
    open_count = 0
    
    if os.path.exists(LEDGER_FILE):
        df = pd.read_csv(LEDGER_FILE, names=['Timestamp', 'Ticker', 'Price', 'Qty', 'Side', 'SL', 'Strategy', 'Status'])
        crypto_df = df[df['Ticker'].isin(['XBTUSD', 'ETHUSD'])]
        
        for _, trade in crypto_df.iterrows():
            entry = float(trade['Price'])
            qty = float(trade['Qty'])
            
            if trade['Status'] == 'PAPER': # Open
                # Logic: We've "spent" the cash, but haven't realized a gain/loss
                crypto_cash -= (entry * qty)
                open_count += 1
            else: # Closed (WIN or LOSS)
                # Logic: We realize the final outcome back into cash
                exit_price = entry + ((entry - float(trade['SL'])) * 4) if "WIN" in trade['Status'] else float(trade['SL'])
                crypto_cash += (exit_price * qty) - (entry * qty) # Simplified realized logic

    print("\n" + "="*50)
    print(" 🦅 TRADE HUNTER | FINALIZED AUDIT")
    print("="*40)
    print(f"[ALPACA STOCKS] Equity: ${float(alpaca.equity):,.2f}")
    print(f"[KRAKEN CRYPTO] Net Virtual Eq: ${crypto_cash:,.2f} | Open: {open_count}")
    print("="*50 + "\n")

if __name__ == "__main__":
    audit_accounts()
