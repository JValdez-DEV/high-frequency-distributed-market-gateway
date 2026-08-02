import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from env_config import BASE_DIR, get_env, get_path

# --- SECURE CREDENTIAL LOADING ---
load_dotenv(dotenv_path=BASE_DIR / '.env')
API_KEY = get_env("ALPACA_API_KEY")
SECRET_KEY = get_env("ALPACA_API_SECRET")

if not API_KEY or not SECRET_KEY:
    raise ValueError("CRITICAL ERROR: Alpaca credentials not found in .env file.")

# --- CONFIGURATION ---
DATA_DIR = get_path(get_env('DATA_DIR', default='massive_data'))
LOOKBACK_DAYS = 180
SYMBOLS = ["QQQ", "SPY", "PLTR", "COIN", "META", "AAPL"]

def fetch_historical_data():
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    
    print(f"\n{'='*60}\nALPACA SECURE INGESTION (BATCH 2: NEW EQUITIES)\n{'='*60}")
    
    for symbol in SYMBOLS:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Requesting {symbol} matrix...")
        
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,
            start=start_date,
            end=end_date
        )
        
        try:
            bars = client.get_stock_bars(request_params)
            df = bars.df
            
            if df.empty:
                print(f"  -> Warning: No data returned for {symbol}.")
                continue
                
            df = df.reset_index()
            df = df.rename(columns={
                "timestamp": "Time", 
                "open": "Open", 
                "high": "High", 
                "low": "Low", 
                "close": "Close", 
                "volume": "Volume"
            })
            df = df.set_index("Time")
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            
            file_path = os.path.join(DATA_DIR, f"{symbol}_1m_master.csv")
            df.to_csv(file_path)
            
            print(f"  -> SUCCESS: Saved {len(df):,} candles to {file_path}")
            
        except Exception as e:
            print(f"  -> ERROR fetching {symbol}: {e}")

if __name__ == "__main__":
    fetch_historical_data()
