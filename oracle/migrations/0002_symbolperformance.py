# Generated migration for SymbolPerformance model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('oracle', '0001_initial'),  # Assumes initial migration exists or will be created
    ]

    operations = [
        migrations.CreateModel(
            name='SymbolPerformance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_price', models.DecimalField(decimal_places=8, max_digits=20)),
                ('roi_1h', models.DecimalField(blank=True, decimal_places=4, help_text='1 hour ROI %', max_digits=10, null=True)),
                ('roi_1d', models.DecimalField(blank=True, decimal_places=4, help_text='1 day ROI %', max_digits=10, null=True)),
                ('roi_1w', models.DecimalField(blank=True, decimal_places=4, help_text='1 week ROI %', max_digits=10, null=True)),
                ('roi_1m', models.DecimalField(blank=True, decimal_places=4, help_text='1 month ROI %', max_digits=10, null=True)),
                ('roi_1y', models.DecimalField(blank=True, decimal_places=4, help_text='1 year ROI %', max_digits=10, null=True)),
                ('volume_24h', models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True)),
                ('volume_change_24h', models.DecimalField(blank=True, decimal_places=4, help_text='24h volume change %', max_digits=10, null=True)),
                ('volatility_24h', models.DecimalField(blank=True, decimal_places=4, help_text='24h volatility %', max_digits=10, null=True)),
                ('high_24h', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('low_24h', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('market_cap', models.DecimalField(blank=True, decimal_places=2, max_digits=30, null=True)),
                ('market_cap_rank', models.IntegerField(blank=True, null=True)),
                ('trades_24h', models.IntegerField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('market_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='oracle.markettype')),
                ('symbol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='performance_metrics', to='oracle.symbol')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='symbolperformance',
            index=models.Index(fields=['symbol', '-timestamp'], name='oracle_symb_symbol__idx'),
        ),
        migrations.AddIndex(
            model_name='symbolperformance',
            index=models.Index(fields=['symbol', 'market_type', '-timestamp'], name='oracle_symb_symbol__mkt_idx'),
        ),
    ]
