from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0008_customer_sales_rep'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriorityCustomer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('custname',   models.CharField(max_length=50)),
                ('custdes',    models.CharField(max_length=200, blank=True)),
                ('agent_code', models.CharField(max_length=50, blank=True)),
                ('agent_name', models.CharField(max_length=200, blank=True)),
                ('status',     models.CharField(max_length=50, blank=True)),
                ('company',    models.CharField(max_length=50)),
                ('synced_at',  models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['custdes'],
            },
        ),
        migrations.AddConstraint(
            model_name='prioritycustomer',
            constraint=models.UniqueConstraint(
                fields=['custname', 'company'],
                name='reports_prioritycustomer_custname_company_uniq',
            ),
        ),
        migrations.AddIndex(
            model_name='prioritycustomer',
            index=models.Index(fields=['company'], name='reports_pri_company_idx'),
        ),
        migrations.AddIndex(
            model_name='prioritycustomer',
            index=models.Index(fields=['agent_code'], name='reports_pri_agent_code_idx'),
        ),
    ]
