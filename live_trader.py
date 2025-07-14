import os
import time
import yfinance as yf
import pandas as pd
from ib_insync import IB, Stock, util
from agent.utils import get_top_strategies
import ta
from datetime import datetime
import pytz

def is_market_open():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    return now.weekday() < 5 and now.hour >= 9 and (now.hour < 16 or (now.hour == 16 and now.minute == 0))

def connect_ibkr():
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)  # Порт 7497 — демо
    print("✅ Connected to IBKR")
    return ib

def load_strategy():
    top_strategies = get_top_strategies(n=1)
    if not top_strategies:
        raise ValueError("❌ No valid strategies found in history.")
    strategy = top_strategies[0]['strategy']
    print(f"🚀 Using strategy: {strategy['name']}")
    return strategy

def fetch_data(ticker, start="2023-01-01", end="2024-01-01"):
    df = yf.download(ticker, start=start, end=end)

    # 🛠 Fix: якщо повернуло tuple, беремо перший елемент
    if isinstance(df, tuple):
        df = df[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [col.lower() for col in df.columns]

    return df

def add_indicators(df):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["ema_10"] = ta.trend.EMAIndicator(df["close"], window=10).ema_indicator()
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["macd"] = ta.trend.MACD(df["close"]).macd()
    df["macd_signal"] = ta.trend.MACD(df["close"]).macd_signal()
    df["volume"] = df["volume"]
    df["std"] = df["close"].rolling(window=14).std()

    # prev
    df["ema_10_prev"] = df["ema_10"].shift(1)
    df["ema_20_prev"] = df["ema_20"].shift(1)
    df["rsi_prev"] = df["rsi"].shift(1)
    df["macd_prev"] = df["macd"].shift(1)
    df["macd_signal_prev"] = df["macd_signal"].shift(1)
    df["volume_prev"] = df["volume"].shift(1)
    df["close_prev"] = df["close"].shift(1)
    df["high"] = df["high"]
    df["low"] = df["low"]

    return df

def evaluate_condition(condition, row):
    context = {k: row.get(k, 0) for k in row.index}
    try:
        return eval(condition, {}, context)
    except Exception as e:
        print(f"⚠️ Condition error: {e}")
        return False

def run_live_trading():
    if not is_market_open():
        print("⛔ Market is closed. Try again later.")
        return

    ib = connect_ibkr()
    strategy = load_strategy()

    tickers = ["IBKR", "NVDA"]

    for ticker in tickers:
        print(f"📊 Processing {ticker}")
        df = fetch_data(ticker)
        df = add_indicators(df)

        latest = df.iloc[-1]

        buy = evaluate_condition(strategy["buy_condition"], latest)
        sell = evaluate_condition(strategy["sell_condition"], latest)

        if buy:
            print(f"📈 BUY signal for {ticker}")
            # Тут можна реалізувати справжню купівлю через IBKR API
        elif sell:
            print(f"📉 SELL signal for {ticker}")
            # Аналогічно - справжній sell
        else:
            print("📉 No action triggered.")

    print("✅ Trading cycle completed.")

if __name__ == "__main__":
    while True:
        run_live_trading()
        time.sleep(60 * 5)  # кожні 5 хвилин