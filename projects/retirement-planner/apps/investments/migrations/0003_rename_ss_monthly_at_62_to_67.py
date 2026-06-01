# Hand-edited: use RenameField to preserve existing data
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0002_remove_ss_at_67_70'),
    ]

    operations = [
        migrations.RenameField(
            model_name='incomesource',
            old_name='ss_monthly_at_62',
            new_name='ss_monthly_at_67',
        ),
    ]
