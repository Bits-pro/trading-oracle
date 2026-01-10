"""
Management command to run backtest validation
"""
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from oracle.backtesting import Backtester


class Command(BaseCommand):
    help = 'Run backtest to validate trading oracle accuracy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to backtest (default: 30)'
        )
        parser.add_argument(
            '--symbols',
            nargs='+',
            default=None,
            help='Specific symbols to backtest (default: all)'
        )
        parser.add_argument(
            '--timeframes',
            nargs='+',
            default=None,
            help='Specific timeframes to backtest (default: all)'
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export detailed results to CSV'
        )

    def handle(self, *args, **options):
        days = options['days']
        symbols = options['symbols']
        timeframes = options['timeframes']
        export = options['export']

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*80}\n'
            f'TRADING ORACLE BACKTEST\n'
            f'{"="*80}\n'
        ))

        self.stdout.write(f'Period: {start_date.date()} to {end_date.date()} ({days} days)')
        if symbols:
            self.stdout.write(f'Symbols: {", ".join(symbols)}')
        if timeframes:
            self.stdout.write(f'Timeframes: {", ".join(timeframes)}')

        # Run backtest
        backtester = Backtester()

        try:
            metrics = backtester.backtest_historical_decisions(
                start_date=start_date,
                end_date=end_date,
                symbols=symbols,
                timeframes=timeframes
            )

            # Print report
            backtester.print_report(metrics)

            # Export if requested
            if export:
                filename = f'backtest_{start_date.date()}_{end_date.date()}.csv'
                backtester.export_results(filename)
                self.stdout.write(self.style.SUCCESS(f'\n✓ Results exported to {filename}'))

            # Interpretation
            self._print_interpretation(metrics)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Backtest failed: {e}'))
            import traceback
            traceback.print_exc()

    def _print_interpretation(self, metrics):
        """Print interpretation of results"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('INTERPRETATION'))
        self.stdout.write(self.style.SUCCESS('='*80))

        # Overall quality assessment
        self.stdout.write('\n📝 Overall Quality:')

        if metrics.win_rate >= 60:
            quality = self.style.SUCCESS('EXCELLENT')
        elif metrics.win_rate >= 50:
            quality = self.style.SUCCESS('GOOD')
        elif metrics.win_rate >= 40:
            quality = self.style.WARNING('ACCEPTABLE')
        else:
            quality = self.style.ERROR('POOR')

        self.stdout.write(f'  Win Rate: {quality} ({metrics.win_rate:.1f}%)')

        if metrics.avg_r >= 1.5:
            r_quality = self.style.SUCCESS('EXCELLENT')
        elif metrics.avg_r >= 1.0:
            r_quality = self.style.SUCCESS('GOOD')
        elif metrics.avg_r >= 0.5:
            r_quality = self.style.WARNING('ACCEPTABLE')
        else:
            r_quality = self.style.ERROR('POOR')

        self.stdout.write(f'  Average R: {r_quality} ({metrics.avg_r:.2f}R)')

        # Confidence calibration
        self.stdout.write('\n🎯 Confidence Calibration:')
        self.stdout.write('  (Does high confidence = high accuracy?)')

        if metrics.metrics_by_confidence:
            for level in ['85-100%', '70-85%', '50-70%', '0-50%']:
                if level in metrics.metrics_by_confidence:
                    data = metrics.metrics_by_confidence[level]
                    self.stdout.write(f'  {level}: {data["win_rate"]:.1f}% win rate ({data["count"]} trades)')

        # Recommendations
        self.stdout.write('\n💡 Recommendations:')

        if metrics.win_rate < 50:
            self.stdout.write(self.style.WARNING(
                '  ⚠ Win rate below 50% - consider adjusting feature weights or filters'
            ))

        if metrics.avg_r < 1.0:
            self.stdout.write(self.style.WARNING(
                '  ⚠ Average R below 1.0 - risk/reward may be too tight or stops too wide'
            ))

        if metrics.max_drawdown > 30:
            self.stdout.write(self.style.WARNING(
                f'  ⚠ Drawdown of {metrics.max_drawdown:.1f}% is high - consider position sizing'
            ))

        # Check confidence calibration
        if metrics.metrics_by_confidence:
            high_conf = metrics.metrics_by_confidence.get('85-100%', {})
            low_conf = metrics.metrics_by_confidence.get('0-50%', {})

            if high_conf and low_conf:
                if high_conf['win_rate'] <= low_conf['win_rate']:
                    self.stdout.write(self.style.WARNING(
                        '  ⚠ Confidence not well calibrated - high confidence not outperforming low'
                    ))

        if metrics.win_rate >= 55 and metrics.avg_r >= 1.0:
            self.stdout.write(self.style.SUCCESS(
                '  ✓ System shows positive expectancy - suitable for live trading with proper risk management'
            ))

        self.stdout.write('\n' + '='*80 + '\n')
