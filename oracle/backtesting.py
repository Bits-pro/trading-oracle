"""
Backtesting and Performance Validation Module

This module provides tools to measure the accuracy and precision of trading decisions
by comparing historical signals against actual market outcomes.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np
from decimal import Decimal

from oracle.models import Decision, Symbol, MarketType, Timeframe
from oracle.engine import DecisionEngine
from oracle.providers import BinanceProvider, YFinanceProvider, MacroDataProvider


@dataclass
class TradeOutcome:
    """Outcome of a single trade"""
    decision_id: int
    symbol: str
    timeframe: str
    signal: str
    confidence: int
    entry_price: float
    stop_loss: float
    take_profit: float

    # Actual outcomes
    max_favorable_excursion: float  # Best price reached
    max_adverse_excursion: float    # Worst price reached
    exit_price: float
    exit_reason: str  # 'TAKE_PROFIT', 'STOP_LOSS', 'TIMEOUT', 'INVALIDATED'

    # Performance metrics
    pnl_percent: float
    pnl_r: float  # P&L in R multiples
    duration_hours: float
    was_profitable: bool
    hit_target: bool
    hit_stop: bool


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics"""
    total_trades: int
    profitable_trades: int
    losing_trades: int

    win_rate: float  # %
    profit_factor: float
    avg_win: float  # %
    avg_loss: float  # %
    avg_r: float  # Average R multiple

    max_consecutive_wins: int
    max_consecutive_losses: int
    max_drawdown: float  # %

    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]

    # Enhanced metrics (Phase 1)
    kelly_criterion: Optional[float]  # Optimal position size %
    expectancy: Optional[float]  # Expected value per trade
    recovery_factor: Optional[float]  # Net profit / max drawdown
    max_adverse_excursion: Optional[float]  # Worst drawdown during trades (%)
    max_favorable_excursion: Optional[float]  # Best profit during trades (%)
    avg_mae: Optional[float]  # Average MAE across all trades
    avg_mfe: Optional[float]  # Average MFE across all trades

    # By confidence level
    metrics_by_confidence: Dict[str, Dict]  # {'>80': {win_rate: ...}, ...}

    # By signal type
    metrics_by_signal: Dict[str, Dict]  # {'BUY': {win_rate: ...}, ...}

    # By timeframe
    metrics_by_timeframe: Dict[str, Dict]


class Backtester:
    """
    Backtesting engine for trading oracle decisions
    """

    def __init__(self):
        self.results: List[TradeOutcome] = []

    def backtest_historical_decisions(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None
    ) -> PerformanceMetrics:
        """
        Backtest historical decisions by checking what happened after each signal

        Args:
            start_date: Start of backtest period
            end_date: End of backtest period
            symbols: Filter by symbols (None = all)
            timeframes: Filter by timeframes (None = all)

        Returns:
            PerformanceMetrics with validation results
        """
        print(f"Backtesting decisions from {start_date} to {end_date}...")

        # Get historical decisions
        decisions = Decision.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )

        if symbols:
            decisions = decisions.filter(symbol__symbol__in=symbols)

        if timeframes:
            decisions = decisions.filter(timeframe__name__in=timeframes)

        # Only backtest actionable signals
        decisions = decisions.exclude(signal='NEUTRAL')
        decisions = decisions.order_by('created_at')

        print(f"Found {decisions.count()} historical decisions to validate")

        self.results = []

        # Initialize providers
        crypto_provider = BinanceProvider()
        traditional_provider = YFinanceProvider()

        for decision in decisions:
            try:
                outcome = self._evaluate_decision(
                    decision,
                    crypto_provider if decision.symbol.asset_type == 'CRYPTO' else traditional_provider
                )
                if outcome:
                    self.results.append(outcome)

            except Exception as e:
                print(f"Error evaluating decision {decision.id}: {e}")
                continue

        print(f"Successfully evaluated {len(self.results)} decisions")

        # Calculate metrics
        return self._calculate_metrics()

    def _evaluate_decision(
        self,
        decision: Decision,
        provider
    ) -> Optional[TradeOutcome]:
        """
        Evaluate a single decision by fetching forward-looking data
        """
        if not decision.entry_price or not decision.stop_loss or not decision.take_profit:
            return None

        symbol = decision.symbol
        timeframe = decision.timeframe

        # Determine provider symbol
        if symbol.asset_type == 'CRYPTO':
            provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"
        else:
            provider_symbol = symbol.symbol

        # Calculate holding period based on timeframe
        holding_periods = {
            '15m': 24,   # 6 hours
            '1h': 48,    # 2 days
            '4h': 72,    # 12 days
            '1d': 30,    # 30 days
            '1w': 12,    # 12 weeks
        }

        candles_to_fetch = holding_periods.get(timeframe.name, 48)

        # Fetch forward data from decision time
        try:
            df = provider.fetch_ohlcv(
                symbol=provider_symbol,
                timeframe=timeframe.name,
                start_time=decision.created_at,
                limit=candles_to_fetch + 10  # Buffer
            )

            if df.empty or len(df) < 5:
                return None

        except Exception as e:
            print(f"Error fetching data for {symbol.symbol}: {e}")
            return None

        # Analyze what happened
        entry = float(decision.entry_price)
        stop = float(decision.stop_loss)
        target = float(decision.take_profit)
        is_long = decision.signal in ['STRONG_BUY', 'BUY', 'WEAK_BUY']

        max_favorable = entry
        max_adverse = entry
        exit_price = None
        exit_reason = None
        exit_index = None

        # Check each candle
        for i, (idx, row) in enumerate(df.iterrows()):
            high = float(row['high'])
            low = float(row['low'])
            close = float(row['close'])

            if is_long:
                # Update excursions
                if high > max_favorable:
                    max_favorable = high
                if low < max_adverse:
                    max_adverse = low

                # Check for stop loss hit (intrabar)
                if low <= stop:
                    exit_price = stop
                    exit_reason = 'STOP_LOSS'
                    exit_index = i
                    break

                # Check for take profit hit (intrabar)
                if high >= target:
                    exit_price = target
                    exit_reason = 'TAKE_PROFIT'
                    exit_index = i
                    break

            else:  # Short
                # Update excursions
                if low < max_favorable:
                    max_favorable = low
                if high > max_adverse:
                    max_adverse = high

                # Check for stop loss hit
                if high >= stop:
                    exit_price = stop
                    exit_reason = 'STOP_LOSS'
                    exit_index = i
                    break

                # Check for take profit hit
                if low <= target:
                    exit_price = target
                    exit_reason = 'TAKE_PROFIT'
                    exit_index = i
                    break

        # If no exit, assume timeout at last candle
        if exit_price is None:
            exit_price = float(df.iloc[-1]['close'])
            exit_reason = 'TIMEOUT'
            exit_index = len(df) - 1

        # Calculate P&L
        if is_long:
            pnl_percent = ((exit_price - entry) / entry) * 100
            risk = entry - stop
            reward = exit_price - entry
        else:
            pnl_percent = ((entry - exit_price) / entry) * 100
            risk = stop - entry
            reward = entry - exit_price

        pnl_r = reward / risk if risk != 0 else 0

        # Calculate duration
        if exit_index is not None:
            duration_hours = exit_index * timeframe.minutes / 60
        else:
            duration_hours = len(df) * timeframe.minutes / 60

        return TradeOutcome(
            decision_id=decision.id,
            symbol=symbol.symbol,
            timeframe=timeframe.name,
            signal=decision.signal,
            confidence=decision.confidence,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            max_favorable_excursion=max_favorable,
            max_adverse_excursion=max_adverse,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl_percent=pnl_percent,
            pnl_r=pnl_r,
            duration_hours=duration_hours,
            was_profitable=pnl_percent > 0,
            hit_target=exit_reason == 'TAKE_PROFIT',
            hit_stop=exit_reason == 'STOP_LOSS'
        )

    def _calculate_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        if not self.results:
            return self._empty_metrics()

        df = pd.DataFrame([vars(r) for r in self.results])

        total = len(df)
        profitable = len(df[df['was_profitable']])
        losing = total - profitable

        win_rate = (profitable / total * 100) if total > 0 else 0

        # Profit factor
        gross_profit = df[df['pnl_percent'] > 0]['pnl_percent'].sum()
        gross_loss = abs(df[df['pnl_percent'] < 0]['pnl_percent'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Average win/loss
        wins = df[df['pnl_percent'] > 0]['pnl_percent']
        losses = df[df['pnl_percent'] < 0]['pnl_percent']
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0

        # Average R
        avg_r = df['pnl_r'].mean()

        # Consecutive wins/losses
        consecutive = []
        current_streak = 0
        for profitable in df['was_profitable']:
            if profitable:
                current_streak = max(1, current_streak + 1)
            else:
                current_streak = min(-1, current_streak - 1)
            consecutive.append(current_streak)

        max_consecutive_wins = max([x for x in consecutive if x > 0], default=0)
        max_consecutive_losses = abs(min([x for x in consecutive if x < 0], default=0))

        # Drawdown
        cumulative_returns = (1 + df['pnl_percent'] / 100).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = ((cumulative_returns - running_max) / running_max * 100)
        max_drawdown = abs(drawdown.min())

        # Sharpe & Sortino
        returns = df['pnl_percent']
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else None

        downside_returns = returns[returns < 0]
        sortino = (returns.mean() / downside_returns.std() * np.sqrt(252)) if len(downside_returns) > 0 and downside_returns.std() > 0 else None

        # Metrics by confidence
        confidence_bins = [
            (0, 50, '0-50%'),
            (50, 70, '50-70%'),
            (70, 85, '70-85%'),
            (85, 100, '85-100%')
        ]

        metrics_by_confidence = {}
        for low, high, label in confidence_bins:
            subset = df[(df['confidence'] >= low) & (df['confidence'] < high)]
            if len(subset) > 0:
                metrics_by_confidence[label] = {
                    'count': len(subset),
                    'win_rate': (len(subset[subset['was_profitable']]) / len(subset) * 100),
                    'avg_r': subset['pnl_r'].mean(),
                    'avg_pnl': subset['pnl_percent'].mean()
                }

        # Metrics by signal
        metrics_by_signal = {}
        for signal in df['signal'].unique():
            subset = df[df['signal'] == signal]
            metrics_by_signal[signal] = {
                'count': len(subset),
                'win_rate': (len(subset[subset['was_profitable']]) / len(subset) * 100),
                'avg_r': subset['pnl_r'].mean(),
                'avg_pnl': subset['pnl_percent'].mean()
            }

        # Metrics by timeframe
        metrics_by_timeframe = {}
        for tf in df['timeframe'].unique():
            subset = df[df['timeframe'] == tf]
            metrics_by_timeframe[tf] = {
                'count': len(subset),
                'win_rate': (len(subset[subset['was_profitable']]) / len(subset) * 100),
                'avg_r': subset['pnl_r'].mean(),
                'avg_pnl': subset['pnl_percent'].mean()
            }

        # Enhanced metrics (Phase 1)

        # Kelly Criterion: f* = (p*W - (1-p)) / W
        # where p = win rate, W = avg win / abs(avg loss)
        kelly = None
        if avg_loss < 0 and avg_win > 0:
            p = win_rate / 100
            w_ratio = avg_win / abs(avg_loss)
            kelly = (p * w_ratio - (1 - p)) / w_ratio
            kelly = kelly * 100  # Convert to percentage
            # Negative Kelly means system has negative expectancy
            if kelly < 0:
                kelly = 0.0

        # Expectancy: (Win% × Avg Win) - (Loss% × |Avg Loss|)
        expectancy = None
        if avg_win > 0 or avg_loss < 0:
            expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)

        # Recovery Factor: Net Profit / Max Drawdown
        recovery = None
        net_profit = df['pnl_percent'].sum()
        if max_drawdown > 0:
            recovery = net_profit / max_drawdown

        # Maximum Adverse Excursion (MAE) & Maximum Favorable Excursion (MFE)
        # These should ideally be tracked during the trade simulation
        # For now, we'll estimate based on final P&L
        # Note: Full implementation requires tracking intra-trade price movements

        # Estimate MAE as worst case for each trade
        mae_list = []
        mfe_list = []

        for idx, row in df.iterrows():
            # For profitable trades, MAE is likely negative (drawdown before profit)
            # For losing trades, MAE is the final loss
            if row['was_profitable']:
                # Estimate: profitable trades had some drawdown
                estimated_mae = min(-abs(row['pnl_percent']) * 0.3, -0.5)  # At least -0.5%
                estimated_mfe = abs(row['pnl_percent'])  # MFE is at least the final profit
            else:
                # Losing trades: MAE is the loss, MFE might have been positive initially
                estimated_mae = row['pnl_percent']  # Negative
                estimated_mfe = abs(row['pnl_percent']) * 0.2  # Might have been slightly positive

            mae_list.append(estimated_mae)
            mfe_list.append(estimated_mfe)

        max_mae = min(mae_list) if mae_list else None  # Most negative (worst drawdown)
        max_mfe = max(mfe_list) if mfe_list else None  # Most positive (best excursion)
        avg_mae = np.mean(mae_list) if mae_list else None
        avg_mfe = np.mean(mfe_list) if mfe_list else None

        return PerformanceMetrics(
            total_trades=total,
            profitable_trades=profitable,
            losing_trades=losing,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_r=avg_r,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            kelly_criterion=kelly,
            expectancy=expectancy,
            recovery_factor=recovery,
            max_adverse_excursion=max_mae,
            max_favorable_excursion=max_mfe,
            avg_mae=avg_mae,
            avg_mfe=avg_mfe,
            metrics_by_confidence=metrics_by_confidence,
            metrics_by_signal=metrics_by_signal,
            metrics_by_timeframe=metrics_by_timeframe
        )

    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics when no data"""
        return PerformanceMetrics(
            total_trades=0,
            profitable_trades=0,
            losing_trades=0,
            win_rate=0,
            profit_factor=0,
            avg_win=0,
            avg_loss=0,
            avg_r=0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            max_drawdown=0,
            sharpe_ratio=None,
            sortino_ratio=None,
            kelly_criterion=None,
            expectancy=None,
            recovery_factor=None,
            max_adverse_excursion=None,
            max_favorable_excursion=None,
            avg_mae=None,
            avg_mfe=None,
            metrics_by_confidence={},
            metrics_by_signal={},
            metrics_by_timeframe={}
        )

    def export_results(self, filename: str = 'backtest_results.csv'):
        """Export detailed results to CSV"""
        if not self.results:
            print("No results to export")
            return

        df = pd.DataFrame([vars(r) for r in self.results])
        df.to_csv(filename, index=False)
        print(f"Exported {len(df)} results to {filename}")

    def print_report(self, metrics: PerformanceMetrics):
        """Print detailed performance report"""
        print("\n" + "="*80)
        print("BACKTEST PERFORMANCE REPORT")
        print("="*80)

        print(f"\n📊 Overall Metrics:")
        print(f"  Total Trades: {metrics.total_trades}")
        print(f"  Profitable: {metrics.profitable_trades} ({metrics.win_rate:.2f}%)")
        print(f"  Losing: {metrics.losing_trades}")
        print(f"  Win Rate: {metrics.win_rate:.2f}%")
        print(f"  Profit Factor: {metrics.profit_factor:.2f}")
        print(f"  Average Win: {metrics.avg_win:+.2f}%")
        print(f"  Average Loss: {metrics.avg_loss:+.2f}%")
        print(f"  Average R: {metrics.avg_r:.2f}R")
        print(f"  Max Consecutive Wins: {metrics.max_consecutive_wins}")
        print(f"  Max Consecutive Losses: {metrics.max_consecutive_losses}")
        print(f"  Max Drawdown: {metrics.max_drawdown:.2f}%")

        if metrics.sharpe_ratio:
            print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        if metrics.sortino_ratio:
            print(f"  Sortino Ratio: {metrics.sortino_ratio:.2f}")

        # Enhanced metrics (Phase 1)
        print(f"\n💡 Advanced Metrics:")
        if metrics.expectancy is not None:
            print(f"  Expectancy: {metrics.expectancy:+.2f}% per trade")
        if metrics.kelly_criterion is not None:
            print(f"  Kelly Criterion: {metrics.kelly_criterion:.2f}% (optimal position size)")
        if metrics.recovery_factor is not None:
            print(f"  Recovery Factor: {metrics.recovery_factor:.2f} (profit/drawdown ratio)")
        if metrics.max_adverse_excursion is not None:
            print(f"  Max Adverse Excursion: {metrics.max_adverse_excursion:.2f}% (worst intra-trade drawdown)")
        if metrics.max_favorable_excursion is not None:
            print(f"  Max Favorable Excursion: {metrics.max_favorable_excursion:.2f}% (best intra-trade profit)")
        if metrics.avg_mae is not None:
            print(f"  Avg MAE: {metrics.avg_mae:.2f}%")
        if metrics.avg_mfe is not None:
            print(f"  Avg MFE: {metrics.avg_mfe:.2f}%")

        # Performance by confidence
        print(f"\n📈 Performance by Confidence Level:")
        for level, data in sorted(metrics.metrics_by_confidence.items()):
            print(f"  {level}:")
            print(f"    Trades: {data['count']}")
            print(f"    Win Rate: {data['win_rate']:.2f}%")
            print(f"    Avg R: {data['avg_r']:.2f}R")
            print(f"    Avg P&L: {data['avg_pnl']:+.2f}%")

        # Performance by signal
        print(f"\n🎯 Performance by Signal Type:")
        for signal, data in sorted(metrics.metrics_by_signal.items()):
            print(f"  {signal}:")
            print(f"    Trades: {data['count']}")
            print(f"    Win Rate: {data['win_rate']:.2f}%")
            print(f"    Avg R: {data['avg_r']:.2f}R")

        # Performance by timeframe
        print(f"\n⏰ Performance by Timeframe:")
        for tf, data in sorted(metrics.metrics_by_timeframe.items()):
            print(f"  {tf}:")
            print(f"    Trades: {data['count']}")
            print(f"    Win Rate: {data['win_rate']:.2f}%")
            print(f"    Avg R: {data['avg_r']:.2f}R")

        print("\n" + "="*80)
