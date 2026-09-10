from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vault", "0002_append_only_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="subjectidentity",
            name="mobile_e164_index",
            field=models.CharField(
                blank=True, db_index=True, max_length=64, null=True, unique=True
            ),
        ),
        migrations.CreateModel(
            name="EnrolmentChallenge",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("mobile_index", models.CharField(db_index=True, max_length=64)),
                ("code_hash", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "enrolment_challenge",
            },
        ),
        migrations.AddIndex(
            model_name="enrolmentchallenge",
            index=models.Index(
                fields=["mobile_index", "-created_at"],
                name="enrolment_c_mobile__idx",
            ),
        ),
    ]
