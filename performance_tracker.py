#!/usr/bin/env python3
import os
import json
import urllib.request
import pandas as pd
import numpy as np
from typing import Dict, Any, List

# --- PATH CONFIGURATION ---
LEDGER_PATH = "/root/trade_hunter/trade_ledger.csv"
METRICS_OUTPUT = "/root/trade_hunter/graduation_report.json"
ENV_PATH = "/root/trade_hunter/.env"

# --- GRADUATION THRESHOLDS ---
MIN_TRADES = 30
REQ_PROFIT_FACTOR = 1.25
REQ_WIN_RATE = 0.25
MAX_ALLOWABLE_DD = 0.07
MAX_ALLOWABLE_SLIPPAGE = 0.0003

def load_webhook() -> str:
    """Parses environment config to extract target Discord webhook."""
    if not os.path.exists(ENV_PATH):
        return ""
    with open(ENV_PATH, "r") as f:
        for line in f:
            if "DISCORD_WEBHOOK_URL" in line:
                return line.split("=")[1].strip().strip('"').strip("'")
    return ""

def send_discord_alert(webhook_url: str, report: Dict[str, Any]) -> None:
    """Dispatches a formatted metric summary block directly to Discord."""
    if not webhook_url:
        return

    m = report["metrics"]
    g = report["gates"]
    grad_status = "🟩 GRADUATION REQUIREMENTS MET" if report["graduation_ready"] else "🟨 IN FORWARD TESTING PROGRESS"

    embed = {
        "title": f"📊 TRADE HUNTER V3.6 SYSTEM STATUS",
        "description": f"**Status:** {grad_status}\nTimestamp: {report['timestamp']}",
        "color": 65280 if report["graduation_ready"] else 16776960,
        "fields": [
            {"name": "Closed Executions", "value": f"{m['total_closed_trades']} / {MIN_TRADES} {'✅' if g['minimum_trades_met'] else '⏳'}", "inline": True},
            {"name": "Net Realized PNL", "value": f"${m['net_pnl']:,}", "inline": True},
            {"name": "Profit Factor", "value": f"{m['profit_factor']} / {REQ_PROFIT_FACTOR} {'✅' if g['profit_factor_passed'] else '❌'}", "inline": True},
            {"name": "Win Rate (4R Base)", "value": f"{m['win_rate']*100:.2f}% / {REQ_WIN_RATE*100}% {'✅' if g['win_rate_passed'] else '❌'}", "inline": True},
            {"name": "Max Peak Drawdown", "value": f"{m['max_drawdown']*100:.2f}% / {MAX_ALLOWABLE_DD*100}% {'✅' if g['drawdown_safeguard_passed'] else '❌'}", "inline": True},
            {"name": "Average Slippage", "value": f"{m['avg_slippage']*10000:.4f} bps / {MAX_ALLOWABLE_SLIPPAGE*10000} bps {'✅' if g['slippage_tolerance_passed'] else '❌'}", "inline": True}
        ],
        "footer": {"text": "Velocity Core Architecture Performance Monitor"}
    }

    payload = json.dumps({"embeds": [embed]}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, 
        data=payload, 
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as response:
            response.read()
    except Exception as e:
        print(f"[-] Discord dispatch failed: {e}")

def reconstruct_closed_trades(df: pd.DataFrame) -> List[Dict[str, Any]]:
    closed_trades = []
    open_positions = {}
    for _, row in df.iterrows():
        if len(row) < 6:
            continue
        ticker = str(row[1]).strip()
        fill_price = float(row[2])
        qty = float(row[3])
        side = str(row[4]).strip().upper()
        signal_price = float(row[5])
        exec_slippage = abs(fill_price - signal_price) / signal_price if signal_price > 0 else 0.0

        if side == "BUY":
            if ticker not in open_positions:
                open_positions[ticker] = []
            open_positions[ticker].append((fill_price, qty, exec_slippage))
        elif side == "SELL" and ticker in open_positions and open_positions[ticker]:
            matched_pnl = 0.0
            total_exit_qty = qty
            slippage_records = [exec_slippage]
            while total_exit_qty > 0 and open_positions[ticker]:
                buy_price, buy_qty, buy_slip = open_positions[ticker][0]
                slippage_records.append(buy_slip)
                if buy_qty <= total_exit_qty:
                    matched_pnl += (fill_price - buy_price) * buy_qty
                    total_exit_qty -= buy_qty
                    open_positions[ticker].pop(0)
                else:
                    matched_pnl += (fill_price - buy_price) * total_exit_qty
                    open_positions[ticker][0] = (buy_price, buy_qty - total_exit_qty, buy_slip)
                    total_exit_qty = 0
            closed_trades.append({
                "ticker": ticker,
                "pnl": matched_pnl,
                "slippage": float(np.mean(slippage_records))
            })
    return closed_trades

def calculate_metrics(closed_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not closed_trades:
        return {"status": "NO_CLOSED_TRADES", "metrics": {"total_closed_trades": 0, "net_pnl": 0.0, "profit_factor": 0.0, "win_rate": 0.0, "max_drawdown": 0.0, "avg_slippage": 0.0}, "gates": {"minimum_trades_met": False, "profit_factor_passed": False, "win_rate_passed": False, "drawdown_safeguard_passed": False, "slippage_tolerance_passed": False}, "graduation_ready": False}

    trade_df = pd.DataFrame(closed_trades)
    total_trades = int(len(trade_df))
    gross_profit = float(trade_df[trade_df['pnl'] > 0]['pnl'].sum())
    gross_loss = float(trade_df[trade_df['pnl'] < 0]['pnl'].abs().sum())
    net_pnl = float(trade_df['pnl'].sum())
    avg_slippage = float(trade_df['slippage'].mean())
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float(gross_profit if gross_profit > 0 else 0.0)
    win_rate = float(len(trade_df[trade_df['pnl'] > 0]) / total_trades)

    trade_df['cum_pnl'] = trade_df['pnl'].cumsum()
    trade_df['equity'] = 100000.0 + trade_df['cum_pnl']
    max_dd = float(((trade_df['equity'].cummax() - trade_df['equity']) / trade_df['equity'].cummax()).max())

    passed_trades = total_trades >= MIN_TRADES
    passed_pf = profit_factor >= REQ_PROFIT_FACTOR
    passed_wr = win_rate >= REQ_WIN_RATE
    passed_dd = max_dd <= MAX_ALLOWABLE_DD
    passed_slip = avg_slippage <= MAX_ALLOWABLE_SLIPPAGE

    return {
        "status": "COMPUTED",
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {"total_closed_trades": total_trades, "net_pnl": round(net_pnl, 2), "profit_factor": round(profit_factor, 2), "win_rate": round(win_rate, 4), "max_drawdown": round(max_dd, 4), "avg_slippage": round(avg_slippage, 6)},
        "gates": {"minimum_trades_met": passed_trades, "profit_factor_passed": passed_pf, "win_rate_passed": passed_wr, "drawdown_safeguard_passed": passed_dd, "slippage_tolerance_passed": passed_slip},
        "graduation_ready": bool(all([passed_trades, passed_pf, passed_wr, passed_dd, passed_slip]))
    }

def main() -> None:
    if not os.path.exists(LEDGER_PATH) or os.path.getsize(LEDGER_PATH) == 0:
        return
    try:
        df = pd.read_csv(LEDGER_PATH, header=None)
        closed_trades = reconstruct_closed_trades(df)
        report = calculate_metrics(closed_trades)
        with open(METRICS_OUTPUT, "w") as f:
            json.dump(report, f, indent=4)
        
        webhook = load_webhook()
        if webhook and report["status"] == "COMPUTED":
            send_discord_alert(webhook, report)
    except Exception as e:
        print(f"[-] Execution error: {e}")

if __name__ == "__main__":
    main()
