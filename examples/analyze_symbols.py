"""
Example: Programmatic analysis using the Trading Oracle

This script shows how to use the trading oracle programmatically
without using the API endpoints.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trading_oracle.settings')
django.setup()

from oracle.models import Symbol, MarketType, Timeframe
from oracle.engine import DecisionEngine
from oracle.providers import BinanceProvider, YFinanceProvider, MacroDataProvider


def analyze_symbol(symbol_code, timeframe_name='1h', market_type_name='SPOT'):
    """
    Analyze a single symbol and return decision

    Args:
        symbol_code: Symbol code (e.g., 'BTCUSDT', 'XAUUSD')
        timeframe_name: Timeframe (e.g., '1h', '4h', '1d')
        market_type_name: Market type (e.g., 'SPOT', 'PERPETUAL')

    Returns:
        DecisionOutput object
    """
    # Get symbol from database
    try:
        symbol = Symbol.objects.get(symbol=symbol_code, is_active=True)
    except Symbol.DoesNotExist:
        print(f"Error: Symbol {symbol_code} not found in database")
        return None

    # Determine provider
    if symbol.asset_type == 'CRYPTO':
        provider = BinanceProvider()
        provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"
    else:
        provider = YFinanceProvider()
        provider_symbol = symbol.symbol

    # Fetch market data
    print(f"Fetching market data for {symbol_code}...")
    df = provider.fetch_ohlcv(
        symbol=provider_symbol,
        timeframe=timeframe_name,
        limit=500
    )

    if df.empty:
        print(f"Error: No market data available for {symbol_code}")
        return None

    print(f"✓ Fetched {len(df)} candles")

    # Fetch macro data
    print("Fetching macro indicators...")
    macro_provider = MacroDataProvider()
    macro_context = macro_provider.fetch_all_macro_indicators()
    print(f"✓ Fetched {len(macro_context)} macro indicators")

    # Build context
    context = {'macro': macro_context}

    # Add derivatives data if needed
    if market_type_name in ['PERPETUAL', 'FUTURES'] and symbol.asset_type == 'CRYPTO':
        print("Fetching derivatives data...")
        try:
            funding = provider.fetch_funding_rate(provider_symbol)
            oi = provider.fetch_open_interest(provider_symbol)

            import pandas as pd
            from datetime import datetime

            context['derivatives'] = {
                'funding_rate': pd.DataFrame([{
                    'timestamp': funding['next_funding_time'] or datetime.now(),
                    'rate': funding['rate']
                }]),
                'open_interest': pd.DataFrame([{
                    'timestamp': oi['timestamp'],
                    'value': oi['open_interest']
                }]),
                'mark_price': funding.get('mark_price'),
                'index_price': funding.get('index_price'),
            }
            print("✓ Fetched derivatives data")
        except Exception as e:
            print(f"Warning: Could not fetch derivatives data: {e}")

    # Run decision engine
    print(f"\nRunning decision engine for {symbol_code} {timeframe_name}...")
    engine = DecisionEngine(
        symbol=symbol_code,
        market_type=market_type_name,
        timeframe=timeframe_name
    )

    decision = engine.generate_decision(df, context)

    return decision


def print_decision(decision):
    """Pretty print a decision"""
    if not decision:
        return

    print("\n" + "="*60)
    print(f"DECISION: {decision.symbol} | {decision.market_type} | {decision.timeframe}")
    print("="*60)
    print(f"\n🎯 Signal: {decision.signal}")
    print(f"📊 Bias: {decision.bias}")
    print(f"💯 Confidence: {decision.confidence}%")

    if decision.entry_price:
        print(f"\n💰 Trade Parameters:")
        print(f"   Entry: {decision.entry_price}")
        print(f"   Stop Loss: {decision.stop_loss}")
        print(f"   Take Profit: {decision.take_profit}")
        print(f"   Risk/Reward: {decision.risk_reward}")

    print(f"\n🔴 Invalidation Conditions:")
    for condition in decision.invalidation_conditions:
        print(f"   - {condition}")

    print(f"\n⭐ Top 5 Drivers:")
    for i, driver in enumerate(decision.top_drivers, 1):
        direction_emoji = "🟢" if driver['direction'] > 0 else "🔴" if driver['direction'] < 0 else "⚪"
        print(f"   {i}. {direction_emoji} {driver['name']} ({driver['category']})")
        print(f"      Contribution: {driver['contribution']:.3f}")
        print(f"      {driver['explanation']}")

    print(f"\n📈 Regime Context:")
    for key, value in decision.regime_context.items():
        print(f"   {key}: {value}")

    print(f"\n📊 Raw Score: {decision.raw_score:.3f}")
    print("="*60)


def analyze_multiple_symbols(symbols, timeframes=['1h', '4h', '1d']):
    """Analyze multiple symbols across multiple timeframes"""
    results = {}

    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"ANALYZING {symbol}")
        print(f"{'='*60}")

        results[symbol] = {}

        for timeframe in timeframes:
            print(f"\n--- {timeframe} ---")
            decision = analyze_symbol(symbol, timeframe)

            if decision:
                results[symbol][timeframe] = decision
                print(f"✓ {decision.signal} | {decision.bias} | Confidence: {decision.confidence}%")
            else:
                print("✗ Analysis failed")

    return results


if __name__ == '__main__':
    # Example 1: Analyze single symbol
    print("Example 1: Single Symbol Analysis")
    print("="*60)
    decision = analyze_symbol('BTCUSDT', '1h', 'SPOT')
    print_decision(decision)

    # Example 2: Analyze multiple symbols
    print("\n\nExample 2: Multiple Symbol Analysis")
    print("="*60)
    symbols = ['BTCUSDT', 'ETHUSDT', 'XAUUSD']
    results = analyze_multiple_symbols(symbols, timeframes=['1h', '1d'])

    # Print summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for symbol, timeframes in results.items():
        print(f"\n{symbol}:")
        for tf, decision in timeframes.items():
            print(f"  {tf}: {decision.signal} ({decision.confidence}%)")
