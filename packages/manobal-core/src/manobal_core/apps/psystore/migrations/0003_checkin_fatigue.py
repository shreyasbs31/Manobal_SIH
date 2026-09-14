from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("psystore", "0002_signal_stores_agent_ruleset"),
    ]

    operations = [
        migrations.AddField(
            model_name="checkinresponse",
            name="fatigue",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
            ),
        ),
    ]
