from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0013_fix_starin_rebate_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='posrecord',
            name='salesperson_override_2',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='override_records_2',
                to='reports.prioritysalesperson',
            ),
        ),
        migrations.AddField(
            model_name='posrecord',
            name='salesperson_split_pct',
            field=models.PositiveSmallIntegerField(
                default=100,
                help_text='% of invoice credited to rep 1 (rest to rep 2). 100 = no split.',
            ),
        ),
    ]
