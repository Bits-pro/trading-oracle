#!/usr/bin/env python3
"""
Test if we can fetch gold data from Yahoo Finance
"""
import yfinance as yf
from datetime import datetime, timedelta

print("Testing Gold Data Fetch")
print("=" * 60)

# Test the ticker we're using
ticker = 'XAUUSD=X'
print(f"\nTrying ticker: {ticker}")

try:
    yf_ticker = yf.Ticker(ticker)

    # Try different periods
    for period in ['1d', '5d']:
        print(f"\nPeriod: {period}, Interval: 1h")
        df = yf_ticker.history(period=period, interval='1h')

        if df.empty:
            print("  ✗ No data returned")
        else:
            print(f"  ✓ Success! {len(df)} candles")
            print(f"    Latest: {df.index[-1]} | Close: ${df['Close'].iloc[-1]:.2f}")
            print(f"    First 3 rows:")
            print(df[['Open', 'High', 'Low', 'Close', 'Volume']].head(3))

except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "=" * 60)
print("\nTrying alternative gold tickers:")

alternatives = [
    ('GC=F', 'Gold Futures'),
    ('GLD', 'Gold ETF'),
]

for alt_ticker, desc in alternatives:
    print(f"\n{desc} ({alt_ticker}):")
    try:
        yf_ticker = yf.Ticker(alt_ticker)
        df = yf_ticker.history(period='1d', interval='1h')

        if df.empty:
            print("  ✗ No data")
        else:
            print(f"  ✓ {len(df)} candles | Latest: ${df['Close'].iloc[-1]:.2f}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
