from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0005_rename_reports_mon_year_43b9a1_idx_reports_mon_year_6b614a_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='distributor',
            name='priority_customer_code',
            field=models.CharField(
                blank=True, max_length=50,
                help_text='Priority CUSTNAME code for this distributor (e.g. CDEV)',
            ),
        ),
        migrations.AddField(
            model_name='distributor',
            name='salesperson_code',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='distributor',
            name='salesperson_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.CreateModel(
            name='PrioritySalesperson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent_code', models.CharField(max_length=50, unique=True)),
                ('agent_name', models.CharField(blank=True, max_length=200)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['agent_name'],
            },
        ),
        migrations.CreateModel(
            name='PriorityProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('part_number', models.CharField(max_length=100, unique=True)),
                ('description', models.CharField(blank=True, max_length=500)),
                ('description_local', models.CharField(blank=True, max_length=500)),
                ('family', models.CharField(blank=True, max_length=100)),
                ('family_description', models.CharField(blank=True, max_length=200)),
                ('status', models.CharField(blank=True, max_length=50)),
                ('synced_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['part_number'],
            },
        ),
    ]
