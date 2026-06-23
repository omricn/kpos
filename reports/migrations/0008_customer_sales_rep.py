import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0007_posrecord_currency_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerSalesRep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(db_index=True, max_length=200)),
                ('effective_from', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('salesperson', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='customer_assignments',
                    to='reports.prioritysalesperson',
                )),
            ],
            options={
                'ordering': ['customer_name', '-effective_from'],
            },
        ),
        migrations.AddIndex(
            model_name='customersalesrep',
            index=models.Index(fields=['customer_name', 'effective_from'], name='reports_cus_custome_idx'),
        ),
        migrations.AddField(
            model_name='posrecord',
            name='salesperson_override',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='override_records',
                to='reports.prioritysalesperson',
            ),
        ),
    ]
