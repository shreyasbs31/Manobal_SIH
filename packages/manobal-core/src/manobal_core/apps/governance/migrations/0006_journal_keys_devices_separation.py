from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("governance", "0005_signal_stores_agent_ruleset"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="separated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="JournalKey",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("subject_token", models.CharField(db_index=True, max_length=64)),
                ("key_id", models.CharField(max_length=64, unique=True)),
                ("wrapped_key", models.BinaryField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("destroyed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "journal_key",
            },
        ),
        migrations.AddIndex(
            model_name="journalkey",
            index=models.Index(
                fields=["subject_token", "destroyed_at"],
                name="journal_key_subject_d_idx",
            ),
        ),
        migrations.CreateModel(
            name="PairedDevice",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("subject_token", models.CharField(db_index=True, max_length=64)),
                ("device_id", models.CharField(max_length=64)),
                ("public_key", models.CharField(max_length=512)),
                ("paired_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "paired_device",
            },
        ),
        migrations.AddConstraint(
            model_name="paireddevice",
            constraint=models.UniqueConstraint(
                fields=["subject_token", "device_id"], name="uniq_paired_device"
            ),
        ),
        migrations.AddIndex(
            model_name="paireddevice",
            index=models.Index(
                fields=["subject_token", "revoked_at"],
                name="paired_devi_subject_r_idx",
            ),
        ),
    ]
