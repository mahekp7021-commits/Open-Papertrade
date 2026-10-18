# Add correction event to the immutable Forex demo ledger.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0027_teaching_board_trade")]

    operations = [
        migrations.AlterField(
            model_name="forextrade",
            name="event_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("OPEN", "Open"),
                    ("CLOSE", "Close"),
                    ("STOP_OUT", "Stop Out"),
                    ("CORRECTION", "Correction"),
                ],
            ),
        ),
    ]
