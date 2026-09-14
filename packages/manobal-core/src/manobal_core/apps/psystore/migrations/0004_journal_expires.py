from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("psystore", "0003_checkin_fatigue"),
    ]

    operations = [
        migrations.AddField(
            model_name="journalentry",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
