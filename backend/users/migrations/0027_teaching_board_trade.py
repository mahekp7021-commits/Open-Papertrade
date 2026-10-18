# Editable classroom board trades; intentionally separate from ForexPosition/ForexTrade.
import decimal
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0026_merge_forex_and_strategy")]
    operations = [
        migrations.CreateModel(
            name="TeachingBoardTrade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol", models.CharField(help_text="Teaching symbol, e.g. USDJPY, BTCUSD or USDBTC.", max_length=12)),
                ("side", models.CharField(choices=[("BUY", "Buy"), ("SELL", "Sell")], default="BUY", max_length=4)),
                ("entry_price", models.DecimalField(decimal_places=8, default=decimal.Decimal("1.00000000"), max_digits=20)),
                ("margin_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=20)),
                ("leverage", models.PositiveIntegerField(default=100)),
                ("lots", models.DecimalField(decimal_places=4, default=decimal.Decimal("0.0100"), max_digits=12)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("CLOSED", "Closed"), ("EXAMPLE", "Teaching example")], default="EXAMPLE", max_length=12)),
                ("trade_time", models.DateTimeField(default=django.utils.timezone.now, help_text="Trainer-editable example date and time.")),
                ("lesson_title", models.CharField(blank=True, default="", max_length=160)),
                ("explanation", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teaching_board_trades", to="users.trainingaccount")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="teaching_board_trades_created", to="users.userprofile")),
            ],
            options={"db_table": "teaching_board_trades", "ordering": ["-trade_time", "-id"]},
        ),
    ]
