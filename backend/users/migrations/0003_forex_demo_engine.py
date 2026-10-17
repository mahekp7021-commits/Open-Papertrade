# Forex training engine tables; separate from the legacy share-based ledger.
import decimal
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_training_classroom"),
    ]

    operations = [
        migrations.CreateModel(
            name="ForexDemoWallet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("balance", models.DecimalField(decimal_places=2, default=decimal.Decimal("100000.00"), max_digits=20)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="forex_wallet", to="users.trainingaccount")),
            ],
            options={"db_table": "forex_demo_wallets"},
        ),
        migrations.CreateModel(
            name="ForexPosition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol", models.CharField(max_length=12)),
                ("side", models.CharField(choices=[("BUY", "Buy"), ("SELL", "Sell")], max_length=4)),
                ("lots", models.DecimalField(decimal_places=4, max_digits=12)),
                ("entry_price", models.DecimalField(decimal_places=6, max_digits=16)),
                ("entry_mid_price", models.DecimalField(decimal_places=6, max_digits=16)),
                ("margin_used", models.DecimalField(decimal_places=2, max_digits=20)),
                ("leverage_at_open", models.PositiveIntegerField()),
                ("spread_pips_at_open", models.DecimalField(decimal_places=3, max_digits=8)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("CLOSED", "Closed")], default="OPEN", max_length=8)),
                ("open_reason", models.TextField()),
                ("opened_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("close_price", models.DecimalField(blank=True, decimal_places=6, max_digits=16, null=True)),
                ("realized_pnl", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=20)),
                ("close_reason", models.TextField(blank=True, default="")),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="forex_positions", to="users.trainingaccount")),
                ("closed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="forex_positions_closed", to="users.userprofile")),
                ("opened_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="forex_positions_opened", to="users.userprofile")),
            ],
            options={"db_table": "forex_positions", "ordering": ["-opened_at"]},
        ),
        migrations.CreateModel(
            name="ForexTrade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("OPEN", "Open"), ("CLOSE", "Close"), ("STOP_OUT", "Stop Out")], max_length=20)),
                ("symbol", models.CharField(max_length=12)),
                ("side", models.CharField(max_length=4)),
                ("lots", models.DecimalField(decimal_places=4, max_digits=12)),
                ("price", models.DecimalField(decimal_places=6, max_digits=16)),
                ("pnl", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=20)),
                ("margin_used", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=20)),
                ("reason", models.TextField()),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="forex_trades", to="users.trainingaccount")),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="forex_trade_events", to="users.userprofile")),
                ("position", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to="users.forexposition")),
            ],
            options={"db_table": "forex_trades", "ordering": ["-created_at"]},
        ),
    ]
