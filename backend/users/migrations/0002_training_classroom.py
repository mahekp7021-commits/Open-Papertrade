# Generated for the training classroom foundation.
import decimal
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrainingAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("TRAINER", "Trainer"), ("TRAINEE", "Trainee")], default="TRAINEE", max_length=10)),
                ("is_enabled", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="training_accounts_created", to="users.userprofile")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="training_account", to="users.userprofile")),
            ],
            options={
                "db_table": "training_accounts",
                "ordering": ["user__name"],
            },
        ),
        migrations.CreateModel(
            name="TrainerTradingConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("leverage", models.PositiveIntegerField(default=100, help_text="Demo leverage, e.g. 100 means 1:100.")),
                ("spread_pips", models.DecimalField(decimal_places=3, default=decimal.Decimal("1.000"), max_digits=8)),
                ("margin_call_level_percent", models.DecimalField(decimal_places=2, default=decimal.Decimal("100.00"), max_digits=7)),
                ("stop_out_level_percent", models.DecimalField(decimal_places=2, default=decimal.Decimal("50.00"), max_digits=7)),
                ("max_position_size", models.DecimalField(decimal_places=4, default=decimal.Decimal("10.0000"), max_digits=20)),
                ("allowed_symbols", models.JSONField(blank=True, default=list, help_text='Allowed demo symbols, e.g. ["EURUSD", "GBPUSD"]. Empty means no per-account allowlist.')),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="trading_config", to="users.trainingaccount")),
            ],
            options={
                "db_table": "trainer_trading_configs",
                "verbose_name": "Trainer Trading Configuration",
                "verbose_name_plural": "Trainer Trading Configurations",
            },
        ),
        migrations.CreateModel(
            name="TrainingNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("body", models.TextField()),
                ("category", models.CharField(choices=[("REVIEW", "Trade Review"), ("RISK", "Risk Management"), ("TIMING", "Entry/Exit Timing"), ("GENERAL", "General Coaching")], default="REVIEW", max_length=20)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coaching_notes", to="users.trainingaccount")),
                ("author", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="training_notes_written", to="users.userprofile")),
                ("trade", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="training_notes", to="users.trade")),
            ],
            options={
                "db_table": "training_notes",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TrainingAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=40)),
                ("reason", models.TextField()),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("account", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to="users.trainingaccount")),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="training_audit_events", to="users.userprofile")),
            ],
            options={
                "db_table": "training_audit_events",
                "ordering": ["-created_at"],
                "verbose_name": "Training Audit Event",
                "verbose_name_plural": "Training Audit Events",
            },
        ),
    ]
