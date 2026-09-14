from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0006_journal_keys_devices_separation"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnitIncident",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("occurred_at", models.DateTimeField(db_index=True)),
                ("category", models.CharField(max_length=64)),
                ("source_system", models.CharField(default="ops", max_length=32)),
                ("external_id", models.CharField(blank=True, default="", max_length=64)),
                ("window_hours", models.PositiveSmallIntegerField(default=72)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "unit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incidents",
                        to="governance.unit",
                    ),
                ),
            ],
            options={
                "db_table": "unit_incident",
                "ordering": ("-occurred_at",),
            },
        ),
        migrations.AddIndex(
            model_name="unitincident",
            index=models.Index(fields=["unit", "-occurred_at"], name="unit_incide_unit_id_7c2a1e_idx"),
        ),
        migrations.AddConstraint(
            model_name="unitincident",
            constraint=models.UniqueConstraint(
                condition=~models.Q(external_id=""),
                fields=("source_system", "external_id"),
                name="uniq_incident_external_id",
            ),
        ),
    ]
