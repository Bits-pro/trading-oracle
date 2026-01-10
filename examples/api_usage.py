"""
Example: Using the Trading Oracle REST API

This script demonstrates how to interact with the trading oracle
through its REST API endpoints.
"""
import requests
import json
import time
from pprint import pprint


BASE_URL = 'http://localhost:8000/api'


def get_symbols():
    """Get all available symbols"""
    response = requests.get(f'{BASE_URL}/symbols/')
    response.raise_for_status()
    return response.json()


def get_features():
    """Get all available features"""
    response = requests.get(f'{BASE_URL}/features/')
    response.raise_for_status()
    return response.json()


def trigger_analysis(symbols, market_types=['SPOT'], timeframes=['1h', '4h', '1d']):
    """
    Trigger a new analysis

    Args:
        symbols: List of symbol codes
        market_types: List of market types
        timeframes: List of timeframes

    Returns:
        Analysis run ID
    """
    payload = {
        'symbols': symbols,
        'market_types': market_types,
        'timeframes': timeframes
    }

    response = requests.post(
        f'{BASE_URL}/decisions/analyze/',
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    response.raise_for_status()
    return response.json()


def check_analysis_status(run_id):
    """Check status of an analysis run"""
    response = requests.get(f'{BASE_URL}/analysis-runs/{run_id}/')
    response.raise_for_status()
    return response.json()


def get_latest_decisions():
    """Get latest decisions for all symbols"""
    response = requests.get(f'{BASE_URL}/decisions/latest/')
    response.raise_for_status()
    return response.json()


def get_decisions_for_symbol(symbol, limit=1):
    """Get decisions for a specific symbol"""
    response = requests.get(
        f'{BASE_URL}/decisions/by_symbol/',
        params={'symbol': symbol, 'limit': limit}
    )
    response.raise_for_status()
    return response.json()


def get_bulk_decisions(symbols):
    """Get latest decisions for multiple symbols"""
    symbols_str = ','.join(symbols)
    response = requests.get(
        f'{BASE_URL}/decisions/bulk/',
        params={'symbols': symbols_str}
    )
    response.raise_for_status()
    return response.json()


def print_decision(decision):
    """Pretty print a decision"""
    print(f"\n{'='*60}")
    print(f"{decision.get('symbol_name')} | {decision.get('market_type_name')} | {decision.get('timeframe_name')}")
    print(f"{'='*60}")
    print(f"Signal: {decision['signal']} | Bias: {decision['bias']} | Confidence: {decision['confidence']}%")

    if decision.get('entry_price'):
        print(f"\nTrade:")
        print(f"  Entry: {decision['entry_price']}")
        print(f"  Stop: {decision['stop_loss']}")
        print(f"  Target: {decision['take_profit']}")
        print(f"  R:R: {decision['risk_reward']}")

    if decision.get('invalidation_conditions'):
        print(f"\nInvalidation:")
        for condition in decision['invalidation_conditions']:
            print(f"  - {condition}")


# Example usage
if __name__ == '__main__':
    print("Trading Oracle API Examples")
    print("="*60)

    # Example 1: Get available symbols
    print("\n1. Getting available symbols...")
    try:
        symbols_response = get_symbols()
        symbols = symbols_response.get('results', [])
        print(f"✓ Found {len(symbols)} symbols:")
        for symbol in symbols[:5]:  # Show first 5
            print(f"  - {symbol['symbol']}: {symbol['name']} ({symbol['asset_type']})")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Example 2: Get available features
    print("\n2. Getting available features...")
    try:
        features_response = get_features()
        features = features_response.get('results', [])
        print(f"✓ Found {len(features)} features:")

        # Group by category
        categories = {}
        for feature in features:
            cat = feature['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(feature['name'])

        for category, feature_names in categories.items():
            print(f"  {category}: {', '.join(feature_names[:3])}...")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Example 3: Trigger new analysis
    print("\n3. Triggering analysis for BTC and ETH...")
    try:
        analysis_result = trigger_analysis(
            symbols=['BTCUSDT', 'ETHUSDT'],
            market_types=['SPOT'],
            timeframes=['1h', '4h']
        )
        run_id = analysis_result['run_id']
        print(f"✓ Analysis queued with ID: {run_id}")
        print(f"  Status: {analysis_result['status']}")

        # Wait for analysis to complete (in production, you'd poll or use webhooks)
        print("  Waiting for analysis to complete...")
        for i in range(10):  # Max 10 attempts
            time.sleep(2)
            status = check_analysis_status(run_id)
            print(f"  Status: {status['status']}")

            if status['status'] in ['COMPLETED', 'FAILED']:
                break

        if status['status'] == 'COMPLETED':
            print(f"✓ Analysis completed!")
            print(f"  Decisions created: {status.get('decisions_created', 0)}")
        else:
            print(f"✗ Analysis failed or timed out")

    except Exception as e:
        print(f"✗ Error: {e}")

    # Example 4: Get latest decisions
    print("\n4. Getting latest decisions...")
    try:
        latest = get_latest_decisions()
        print(f"✓ Retrieved {len(latest)} latest decisions")

        if latest:
            print("\nSample decision:")
            print_decision(latest[0])
    except Exception as e:
        print(f"✗ Error: {e}")

    # Example 5: Get decisions for specific symbol
    print("\n5. Getting decisions for BTCUSDT...")
    try:
        btc_decisions = get_decisions_for_symbol('BTCUSDT')
        print(f"✓ Retrieved decisions for BTC")

        # Print decisions by market type and timeframe
        for market_type, timeframes in btc_decisions.get('decisions', {}).items():
            print(f"\n  {market_type}:")
            for tf, decisions in timeframes.items():
                if decisions:
                    decision = decisions[0]  # Latest
                    print(f"    {tf}: {decision['signal']} ({decision['confidence']}%)")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Example 6: Bulk query multiple symbols
    print("\n6. Bulk query for multiple symbols...")
    try:
        bulk_results = get_bulk_decisions(['BTCUSDT', 'ETHUSDT', 'XAUUSD'])
        print(f"✓ Retrieved bulk decisions for {len(bulk_results)} symbols")

        for symbol_data in bulk_results:
            print(f"\n  {symbol_data['symbol']} ({symbol_data['asset_type']}):")
            decisions = symbol_data.get('decisions', [])
            if decisions and len(decisions) > 0:
                # Show first decision
                first_decision = decisions[0]
                print(f"    Signal: {first_decision.get('signal', 'N/A')}")
                print(f"    Confidence: {first_decision.get('confidence', 0)}%")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n" + "="*60)
    print("Examples complete!")
    print("\nFor more details, visit: http://localhost:8000/api/")
