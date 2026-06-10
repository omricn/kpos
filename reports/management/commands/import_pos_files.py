import os
import openpyxl
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils.text import slugify
from reports.models import Distributor, POSUpload, POSRecord
from reports.parsers import get_parser

_CANDIDATE_DIRS = [
    r"C:\Users\ocohen\OneDrive - Kramer Electronics Ltd\POS Project",
    "/app/pos_files",
]

def _find_pos_dir():
    for d in _CANDIDATE_DIRS:
        if os.path.isdir(d):
            return d
    return None

POS_DIR = _find_pos_dir() or _CANDIDATE_DIRS[0]

IMPORT_CONFIG = [
    # APAC files
    {'file': 'Q1_2026_POS_ASEAN.xlsx',          'parser': 'asean',          'region': 'APAC', 'period': 'Q1 2026'},
    {'file': 'Q1_2026_POS_GreaterChina.xlsx',   'parser': 'asean',          'region': 'APAC', 'period': 'Q1 2026'},
    {'file': 'Q1_2026_POS_Northeast Asia.xlsx', 'parser': 'asean',          'region': 'APAC', 'period': 'Q1 2026'},
    {'file': 'Q1_2026_POS_Oceania.xlsx',        'parser': 'asean',          'region': 'APAC', 'period': 'Q1 2026'},
    {'file': 'Q1_2026_POS_SAARC.xlsx',          'parser': 'asean',          'region': 'APAC', 'period': 'Q1 2026'},
    # EMEA files (new)
    # Direct and Disti Sales 2026.xlsx excluded:
    #   ALSO FI, Netsmart, Captech are duplicates of Kramer_Reports_20260519 (Bomisco)
    #   F9 unique rows already merged into Bomisco upload
    #   Fineman and Midwich have no overlap — import separately if needed
    {'file': 'Kramer and ZeeVee sales.xlsx',             'parser': 'midwich-zeevee', 'region': 'EMEA', 'period': 'Q1 2026'},
    {'file': 'Kramer_Reports_20260519.xlsx',              'parser': 'emea-bomisco',   'region': 'EMEA', 'period': '2024-2026'},
]

# Codes that should not be touched by this command
PROTECTED_CODES = {'cdev'}


def _get_or_create_distributor(vendor_name, region):
    code = slugify(vendor_name)[:50] or 'unknown'
    dist, _ = Distributor.objects.get_or_create(
        code=code,
        defaults={'name': vendor_name, 'region': region},
    )
    if dist.region != region:
        dist.region = region
        dist.save(update_fields=['region'])
    return dist


class Command(BaseCommand):
    help = 'Import Q1 2026 POS files, creating one Distributor per actual company'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Re-import even if records already exist')

    def handle(self, *args, **options):
        force = options['force']

        # Update CDEV region
        Distributor.objects.filter(code='cdev').update(region='EMEA')
        self.stdout.write('  Updated CDEV region -> EMEA')

        # Remove old regional grouping distributors (not real companies)
        old_codes = {'asean', 'greater-china', 'northeast-asia', 'oceania', 'saarc'}
        removed = Distributor.objects.filter(code__in=old_codes).count()
        if removed:
            Distributor.objects.filter(code__in=old_codes).delete()
            self.stdout.write(f'  Removed {removed} old regional placeholder distributors')

        for cfg in IMPORT_CONFIG:
            filepath = os.path.join(POS_DIR, cfg['file'])
            if not os.path.exists(filepath):
                self.stdout.write(self.style.WARNING(f"  SKIP {cfg['file']} — not found"))
                continue

            self.stdout.write(f"\n  Processing: {cfg['file']} ({cfg['region']})")

            parser = get_parser(cfg.get('parser', 'asean'))
            wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
            all_records = parser(wb)

            if not all_records:
                self.stdout.write(self.style.WARNING(f"    No records parsed"))
                continue

            # Group records by vendor (actual distributor company name)
            by_vendor = defaultdict(list)
            for rec in all_records:
                vendor = rec.get('vendor', '').strip() or 'Unknown'
                by_vendor[vendor].append(rec)

            for vendor_name, records in by_vendor.items():
                dist = _get_or_create_distributor(vendor_name, cfg['region'])

                if not force and dist.records.filter(
                    upload__original_filename=cfg['file']
                ).exists():
                    self.stdout.write(f"    SKIP {vendor_name} — already imported (--force to redo)")
                    continue

                # Remove records from this specific file for this distributor
                dist.uploads.filter(original_filename=cfg['file']).delete()

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
                self.stdout.write(
                    self.style.SUCCESS(f"    OK  {vendor_name} — {len(records)} records")
                )

        self.stdout.write(self.style.SUCCESS('\nImport complete.'))
        self.stdout.write('Refreshing monthly exchange rates...')
        call_command('update_monthly_rates', stdout=self.stdout)
