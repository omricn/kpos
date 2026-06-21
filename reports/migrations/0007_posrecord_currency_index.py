from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_priority'),
    ]

    operations = [
        migrations.AlterField(
            model_name='posrecord',
            name='currency',
            field=models.CharField(blank=True, db_index=True, max_length=10),
        ),
    ]
