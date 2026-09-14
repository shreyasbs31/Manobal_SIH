from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0007_unit_incident"),
    ]

    operations = [
        migrations.AddField(
            model_name="officerprofile",
            name="duty_phone_e164",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="officerprofile",
            name="push_token",
            field=models.CharField(blank=True, default="", max_length=4096),
        ),
    ]
