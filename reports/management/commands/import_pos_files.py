import os
import openpyxl
from django.core.management.base import BaseCommand
from reports.models import Distributor, POSUpload, POSRecord
from reports.parsers import get_parser

POS_DIR = r"C:\Users\ocohen\OneDrive - Kramer Electronics Ltd\POS Project"

IMPORT_CONFIG = [
    {
        'file': 'Q1_2026_POS_ASEAN.xlsx',
        'code': 'asean',
        'name': 'APAC – ASEAN',
        'region': 'ASEAN',
        'period': 'Q1 2026',
    },
    {
        'file': 'Q1_2026_POS_GreaterChina.xlsx',
        'code': 'greater-china',
        'name': 'APAC – Greater China',
        'region': 'Greater China',
        'period': 'Q1 2026',
    },
    {
        'file': 'Q1_2026_POS_Northeast Asia.xlsx',
        'code': 'northeast-asia',
        'name': 'APAC – Northeast Asia',
        'region': 'Northeast Asia',
        'period': 'Q1 2026',
    },
    {
        'file': 'Q1_2026_POS_Oceania.xlsx',
        'code': 'oceania',
        'name': 'APAC – Oceania',
        'region': 'Oceania',
        'period': 'Q1 2026',
    },
    {
        'file': 'Q1_2026_POS_SAARC.xlsx',
        'code': 'saarc',
        'name': 'APAC – SAARC',
        'region': 'SAARC',
        'period': 'Q1 2026',
    },
]


class Command(BaseCommand):
    help = 'Import Q1 2026 POS files for all APAC regions'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Re-import even if records already exist')

    def handle(self, *args, **options):
        force = options['force']

        # Update CDEV region to Europe
        Distributor.objects.filter(code='cdev').update(region='Europe')
        self.stdout.write('  Updated CDEV region -> Europe')

        for cfg in IMPORT_CONFIG:
            filepath = os.path.join(POS_DIR, cfg['file'])
            if not os.path.exists(filepath):
                self.stdout.write(self.style.WARNING(f"  SKIP {cfg['file']} — file not found"))
                continue

            dist, created = Distributor.objects.get_or_create(
                code=cfg['code'],
                defaults={
                    'name': cfg['name'],
                    'region': cfg['region'],
                    'country': 'Multi',
                },
            )
            if not created:
                dist.name = cfg['name']
                dist.region = cfg['region']
                dist.save()

            if not force and dist.records.exists():
                self.stdout.write(f"  SKIP {cfg['name']} — already has data (use --force to reimport)")
                continue

            # Clear existing records for this distributor
            POSRecord.objects.filter(distributor=dist).delete()
            dist.uploads.all().delete()

            parser = get_parser(cfg['code'])
            wb = openpyxl.load_workbook(filepath, data_only=True)
            records = parser(wb)

            if not records:
                self.stdout.write(self.style.WARNING(f"  WARN {cfg['name']} — no records parsed"))
                continue

            upload = POSUpload.objects.create(
                distributor=dist,
                original_filename=cfg['file'],
                report_period=cfg['period'],
                row_count=len(records),
            )

            POSRecord.objects.bulk_create([
                POSRecord(upload=upload, distributor=dist, **r)
                for r in records
            ])

            self.stdout.write(self.style.SUCCESS(f"  OK  {cfg['name']} — {len(records)} records"))

        self.stdout.write(self.style.SUCCESS('\nImport complete.'))
