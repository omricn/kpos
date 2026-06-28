from django.db import migrations
from datetime import date


USA_REBATES = [
    # (customer_name, threshold_q, threshold_yr, rebate_pct, classification, dist_code, pc_custname, pc_company)
    ('ACCU-TECH CORPORATION',          '250000.00', '1000000.00', '0.0300', 'Distributor Standard', 'accu-tech',       'C106918', 'kusa21'),
    ('RESIDEO LLC',                    '500000.00', '2000000.00', '0.0400', 'Distributor Platinum', 'resideo',         'C113334', 'kusa21'),
    ('ALMO, USA',                      '500000.00', '2000000.00', '0.0400', 'Distributor Platinum', 'almo',            'C107155', 'kusa21'),
    ('ANIXTER INC.',                   '250000.00', '1000000.00', '0.0300', 'Distributor Standard', 'anixter',         'C105190', 'kusa21'),
    ('BTX',                            '250000.00', '1000000.00', '0.0300', 'Distributor Standard', 'btx',             'C701003', 'kusa21'),
    ('GRAYBAR ELECTRIC COMPANY, INC.', '250000.00', '1000000.00', '0.0300', 'Distributor Standard', 'graybar',        'C701045', 'kusa21'),
    ('JB&A DISTRIBUTION',              '500000.00', '2000000.00', '0.0400', 'Distributor Platinum', 'jba',             'D064532', 'kusa21'),
    ('STARIN',                         '250000.00', '1000000.00', '0.0300', 'Distributor Standard', None,              'C106101', 'kusa21'),
    ('TD SYNNEX CORPORATION',          '500000.00', '2000000.00', '0.0400', 'Distributor Platinum', 'td-synnex',       'C108076', 'kusa21'),
    ('TOWER PRODUCTS',                 '250000.00', '1000000.00', '0.0300', 'Distributor Standard', 'tower-products',  'C701001', 'kusa21'),
    ('B&H PHOTO & ELECTRONICS CORP.',  '650000.00', '2600000.00', '0.1000', 'Special program',      None,              'C701042', 'kusa21'),
    ('AB Distributing',                '600000.00', '2400000.00', '0.0600', 'Distributor Platinum', 'ab-distributing', 'D245184', 'kusa21'),
    ('CLARK POWELL ASSOCIATES INC.',   '100000.00',  '400000.00', '0.0600', 'Dealer Platinum',      'clark-powell',    'C105103', 'kusa21'),
]


def seed_rebates(apps, schema_editor):
    RebateAgreement  = apps.get_model('reports', 'RebateAgreement')
    Distributor      = apps.get_model('reports', 'Distributor')
    PriorityCustomer = apps.get_model('reports', 'PriorityCustomer')

    if RebateAgreement.objects.exists():
        return  # already seeded (local dev ran the import script)

    effective_from = date(2026, 1, 1)

    for (name, thr_q, thr_yr, pct, classification, dist_code, pc_custname, pc_company) in USA_REBATES:
        dist = Distributor.objects.filter(code=dist_code).first() if dist_code else None
        pc   = PriorityCustomer.objects.filter(custname=pc_custname, company=pc_company).first()

        RebateAgreement.objects.create(
            customer_name       = name,
            threshold_quarterly = thr_q,
            threshold_yearly    = thr_yr,
            rebate_pct          = pct,
            classification      = classification,
            country             = 'USA',
            country_for_accrual = 'USA',
            currency            = 'USD',
            effective_from      = effective_from,
            active              = True,
            source_file         = 'Distys Rebstes - USA.xlsx',
            distributor         = dist,
            priority_customer   = pc,
        )

    print(f'  Seeded {RebateAgreement.objects.count()} USA rebate agreements')


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0011_rebate_agreement'),
    ]

    operations = [
        migrations.RunPython(seed_rebates, migrations.RunPython.noop),
    ]
