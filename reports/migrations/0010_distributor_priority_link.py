import django.db.models.deletion
from django.db import migrations, models


def link_existing_distributors(apps, schema_editor):
    """Auto-link distributors that already have priority_customer_code to PriorityCustomer."""
    Distributor = apps.get_model('reports', 'Distributor')
    PriorityCustomer = apps.get_model('reports', 'PriorityCustomer')

    linked = skipped_ambiguous = skipped_notfound = 0
    for dist in Distributor.objects.exclude(priority_customer_code=''):
        code = dist.priority_customer_code.strip()
        matches = list(PriorityCustomer.objects.filter(custname=code))
        if len(matches) == 1:
            dist.priority_customer = matches[0]
            dist.priority_company = matches[0].company
            dist.save(update_fields=['priority_customer', 'priority_company'])
            linked += 1
        elif len(matches) > 1:
            # Same code in multiple companies — can't auto-resolve, leave for manual admin fix
            skipped_ambiguous += 1
        else:
            skipped_notfound += 1

    print(f'  Distributor->PriorityCustomer: {linked} linked, '
          f'{skipped_ambiguous} ambiguous, {skipped_notfound} not found')


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0009_priority_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='distributor',
            name='priority_company',
            field=models.CharField(
                blank=True, max_length=50,
                help_text='Priority company entity this customer belongs to (e.g. kusa21, sngpr)',
            ),
        ),
        migrations.AddField(
            model_name='distributor',
            name='priority_customer',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='distributors',
                to='reports.prioritycustomer',
                help_text='Linked PriorityCustomer record (same real-world entity)',
            ),
        ),
        migrations.RunPython(link_existing_distributors, migrations.RunPython.noop),
    ]
