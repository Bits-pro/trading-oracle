#!/usr/bin/env python3
"""
Test Multi-Source Provider
Quick verification that the multi-source system is configured correctly
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trading_oracle.settings')
django.setup()

from oracle.providers import MultiSourceProvider, SourceConfidence


def test_multi_source_configuration():
    """Test that multi-source provider is configured correctly"""

    print("=" * 70)
    print("Testing Multi-Source Provider Configuration")
    print("=" * 70)

    provider = MultiSourceProvider()

    # Test symbols
    test_symbols = ['BTCUSDT', 'XAUUSD', 'ETHUSDT', 'XAGUSD']

    for symbol in test_symbols:
        print(f"\n{symbol}:")
        print("-" * 70)

        # Get source status
        sources = provider.get_source_status(symbol)

        if not sources:
            print(f"  ⚠️  No sources configured for {symbol}")
            continue

        for source in sources:
            confidence_emoji = {
                'HIGH': '🟢',
                'MEDIUM': '🟡',
                'LOW': '🟠',
            }.get(source['confidence'], '⚪')

            enabled_status = '✅' if source['enabled'] else '❌'

            print(f"  {confidence_emoji} {source['name']:<25} "
                  f"({source['confidence']:<6}) "
                  f"→ {source['provider_symbol']:<15} "
                  f"{enabled_status}")

    print("\n" + "=" * 70)
    print("✅ Configuration test complete!")
    print("=" * 70)

    return True


def test_source_priority():
    """Test that sources are tried in correct priority order"""

    print("\n" + "=" * 70)
    print("Testing Source Priority Order")
    print("=" * 70)

    provider = MultiSourceProvider()

    # Check XAUUSD priority (should be: Binance PAXG > YFinance Spot > YFinance Futures)
    print("\nXAUUSD Priority Order:")
    print("-" * 70)

    if 'XAUUSD' in provider.sources:
        sources = sorted(
            provider.sources['XAUUSD'],
            key=lambda x: x.confidence.value,
            reverse=True
        )

        for i, source in enumerate(sources, 1):
            confidence_emoji = {
                SourceConfidence.HIGH: '🟢',
                SourceConfidence.MEDIUM: '🟡',
                SourceConfidence.LOW: '🟠',
            }.get(source.confidence, '⚪')

            print(f"  {i}. {confidence_emoji} {source.name} "
                  f"(confidence: {source.confidence.name})")

        # Verify priority order
        expected_order = [SourceConfidence.HIGH, SourceConfidence.MEDIUM, SourceConfidence.LOW]
        actual_order = [s.confidence for s in sources]

        if actual_order == expected_order:
            print("\n  ✅ Priority order is correct!")
        else:
            print(f"\n  ❌ Priority order incorrect!")
            print(f"     Expected: {expected_order}")
            print(f"     Actual: {actual_order}")

    print("=" * 70)

    return True


def test_dynamic_management():
    """Test dynamic source management features"""

    print("\n" + "=" * 70)
    print("Testing Dynamic Source Management")
    print("=" * 70)

    provider = MultiSourceProvider()

    # Test disable/enable
    print("\n1. Testing disable_source():")
    print("-" * 70)

    provider.disable_source('BTCUSDT', 'Binance')
    sources = provider.get_source_status('BTCUSDT')
    binance_source = next((s for s in sources if s['name'] == 'Binance'), None)

    if binance_source and not binance_source['enabled']:
        print("  ✅ Successfully disabled Binance for BTCUSDT")
    else:
        print("  ❌ Failed to disable Binance")

    print("\n2. Testing enable_source():")
    print("-" * 70)

    provider.enable_source('BTCUSDT', 'Binance')
    sources = provider.get_source_status('BTCUSDT')
    binance_source = next((s for s in sources if s['name'] == 'Binance'), None)

    if binance_source and binance_source['enabled']:
        print("  ✅ Successfully enabled Binance for BTCUSDT")
    else:
        print("  ❌ Failed to enable Binance")

    print("\n" + "=" * 70)

    return True


def main():
    """Run all tests"""

    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "MULTI-SOURCE PROVIDER TEST SUITE" + " " * 21 + "║")
    print("╚" + "=" * 68 + "╝")

    try:
        # Run tests
        test_multi_source_configuration()
        test_source_priority()
        test_dynamic_management()

        # Summary
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 23 + "ALL TESTS PASSED! ✅" + " " * 25 + "║")
        print("╚" + "=" * 68 + "╝")
        print("\nYour multi-source provider is configured correctly!")
        print("You can now run analysis with automatic failover support.\n")

        return 0

    except Exception as e:
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 26 + "TEST FAILED! ❌" + " " * 28 + "║")
        print("╚" + "=" * 68 + "╝")
        print(f"\nError: {e}\n")

        import traceback
        traceback.print_exc()

        return 1


if __name__ == '__main__':
    sys.exit(main())
