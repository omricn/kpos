import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0010_distributor_priority_link'),
    ]

    operations = [
        migrations.CreateModel(
            name='RebateAgreement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name',       models.CharField(max_length=200)),
                ('country',             models.CharField(max_length=100, blank=True)),
                ('country_for_accrual', models.CharField(max_length=100, blank=True)),
                ('classification',      models.CharField(max_length=100, blank=True)),
                ('currency',            models.CharField(max_length=10, default='USD')),
                ('threshold_quarterly', models.DecimalField(max_digits=14, decimal_places=2)),
                ('threshold_yearly',    models.DecimalField(max_digits=14, decimal_places=2)),
                ('rebate_pct',          models.DecimalField(max_digits=6, decimal_places=4)),
                ('effective_from',      models.DateField()),
                ('effective_to',        models.DateField(null=True, blank=True)),
                ('active',              models.BooleanField(default=True)),
                ('source_file',         models.CharField(max_length=255, blank=True)),
                ('created_at',          models.DateTimeField(auto_now_add=True)),
                ('updated_at',          models.DateTimeField(auto_now=True)),
                ('distributor', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='rebate_agreements',
                    to='reports.distributor',
                )),
                ('priority_customer', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='rebate_agreements',
                    to='reports.prioritycustomer',
                )),
            ],
            options={'ordering': ['customer_name']},
        ),
        migrations.AddIndex(
            model_name='rebateagreement',
            index=models.Index(fields=['active', 'effective_from'], name='reports_reb_active_idx'),
        ),
    ]
