from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_exchangerate'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonthlyRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField()),
                ('month', models.IntegerField()),
                ('currency', models.CharField(max_length=3)),
                ('rate_to_usd', models.DecimalField(decimal_places=6, max_digits=12)),
                ('rate_to_eur', models.DecimalField(decimal_places=6, max_digits=12)),
            ],
            options={
                'indexes': [models.Index(fields=['year', 'month', 'currency'], name='reports_mon_year_43b9a1_idx')],
            },
        ),
        migrations.AlterUniqueTogether(
            name='monthlyrate',
            unique_together={('year', 'month', 'currency')},
        ),
    ]
