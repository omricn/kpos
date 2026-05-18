from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='distributor',
            name='region',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='posrecord',
            name='country',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
