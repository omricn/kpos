from django.db import migrations


def fix_starin_link(apps, schema_editor):
    RebateAgreement = apps.get_model('reports', 'RebateAgreement')
    Distributor     = apps.get_model('reports', 'Distributor')

    starin_dist = Distributor.objects.filter(code='starin').first()
    if not starin_dist:
        return

    updated = RebateAgreement.objects.filter(
        customer_name='STARIN',
        distributor__isnull=True,
    ).update(distributor=starin_dist)

    if updated:
        print(f'  Fixed STARIN rebate agreement -> distributor={starin_dist.name}')


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0012_seed_usa_rebate_agreements'),
    ]

    operations = [
        migrations.RunPython(fix_starin_link, migrations.RunPython.noop),
    ]
