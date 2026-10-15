from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0002_remove_challenge_user_remove_freepass_user_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitplan",
            name="visit_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="visitplan",
            name="start_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="visitplan",
            name="end_time",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
