from django.db import migrations


# نسخة ثابتة من DEFAULT_INTEREST_WEIGHTS وقت إنشاء الـ migration
DEFAULT_INTEREST_WEIGHTS = {
    "التقنية": {"tech": 1.0},
    "الذكاء الاصطناعي": {"tech": 1.0},
    "الابتكار": {"tech": 0.8, "global": 0.3},
    "الفضاء": {"tech": 1.0, "entertainment": 0.3},
    "الاستدامة": {"sustainability": 1.0},
    "الطاقة": {"sustainability": 0.8, "tech": 0.4},
    "البيئة": {"sustainability": 1.0},
    "الثقافة": {"heritage": 0.7, "global": 0.8},
    "التاريخ والتراث": {"heritage": 1.0},
    "الفنون": {"heritage": 0.7, "entertainment": 0.4},
    "الصحة": {"family": 0.5, "sustainability": 0.4},
    "الترفيه": {"entertainment": 1.0, "family": 0.5},
    "الألعاب": {"entertainment": 1.0, "family": 0.6},
    "الطعام": {"food": 1.0, "global": 0.3},
    "التسوق": {"entertainment": 0.5, "global": 0.5},
}


def fill_weights(apps, schema_editor):
    Interest = apps.get_model("planner", "Interest")

    for interest in Interest.objects.all():
        weights = DEFAULT_INTEREST_WEIGHTS.get(interest.name)

        if weights and not interest.model_weights:
            interest.model_weights = weights
            interest.save(update_fields=["model_weights"])


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0004_interest_model_weights"),
    ]

    operations = [
        migrations.RunPython(fill_weights, migrations.RunPython.noop),
    ]
