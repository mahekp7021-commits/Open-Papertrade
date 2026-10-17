# Merge the existing strategy/backtest migration branch with the Forex classroom branch.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_forex_demo_engine"),
        ("users", "0025_strategy_backtest"),
    ]

    operations = []
