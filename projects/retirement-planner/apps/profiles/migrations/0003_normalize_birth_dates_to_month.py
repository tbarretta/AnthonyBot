from django.db import migrations


def normalize_birth_dates(apps, schema_editor):
    """Scrub the day from all existing birth dates — store only month + year (day=1)."""
    UserProfile = apps.get_model("profiles", "UserProfile")
    SpouseProfile = apps.get_model("profiles", "SpouseProfile")

    for profile in UserProfile.objects.exclude(birth_date__day=1):
        profile.birth_date = profile.birth_date.replace(day=1)
        profile.save(update_fields=["birth_date"])

    for spouse in SpouseProfile.objects.exclude(birth_date__day=1):
        spouse.birth_date = spouse.birth_date.replace(day=1)
        spouse.save(update_fields=["birth_date"])


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0002_remove_retirement_age_risk_from_profile_add_to_scenario"),
    ]

    operations = [
        migrations.RunPython(normalize_birth_dates, migrations.RunPython.noop),
    ]
