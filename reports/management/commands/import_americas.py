"""
Import Americas POS files from the 'From Karina' OneDrive folder.

Strategy:
- STARIN: YTD cumulative files — import only the LATEST (covers Jan-May).
- Monthly distribution files: extract only Graybar / ADI / Tower / TD Synnex.
  (ALMO, Anixter, STARIN, JB&A, AccuTech sheets in those files are skipped;
   we have individual files for those distributors.)
- Anixter: Americas-only rows (EMEA rows filtered in the parser).
- ACCU-TECH: both main format and DDP format files.
"""
import os
import glob
import openpyxl
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils.text import slugify
from reports.models import Distributor, POSUpload, POSRecord
from reports.parsers import get_parser
from reports.views import normalize_country

KARINA_DIR = r"C:\Users\ocohen\OneDrive - Kramer Electronics Ltd\POS Project\From Karina"
REGION = 'Americas'


def _find(pattern):
    """Glob relative to KARINA_DIR, return sorted list of absolute paths."""
    return sorted(glob.glob(os.path.join(KARINA_DIR, pattern), recursive=True))


def _get_or_create_dist(vendor_name):
    code = slugify(vendor_name)[:50] or 'unknown'
    dist, _ = Distributor.objects.get_or_create(
        code=code,
        defaults={'name': vendor_name, 'region': REGION},
    )
    if dist.region != REGION:
        dist.region = REGION
        dist.save(update_fields=['region'])
    return dist


# ---------------------------------------------------------------------------
# File manifest
# Each entry: (glob_pattern, parser_code, period_label)
# For STARIN we glob for the June-1 file (latest YTD = Jan-May).
# ---------------------------------------------------------------------------
MANIFEST = [
    # ALMO Kramer — monthly
    ('**/ALMO KRAMER2026-01.xlsx',  'almo', 'Jan 2026'),
    ('**/ALMO KRAMER2026-02.xlsx',  'almo', 'Feb 2026'),
    ('**/ALMO KRAMER2026-03.xlsx',  'almo', 'Mar 2026'),
    ('**/ALMO KRAMER2026-04.xlsx',  'almo', 'Apr 2026'),
    # ALMO ZeeVee files are identical to KRAMER files — excluded to avoid duplicates
    # STARIN — only the latest YTD (June 1 file = Jan-May)
    ('**/STARIN*YTD*060126*.xlsx',  'starin-ytd', 'Jan-May 2026'),
    # JB&A
    ('**/JB&A*January*.xlsx',       'jba', 'Jan 2026'),
    # ACCU-TECH DDP format (must come before main to win the seen_files race)
    ('**/ACCU*TECH*DDP*JAN*.xlsx',  'accutech-ddp', 'Jan 2026'),
    ('**/ACCU*TECH*DDP*MAR*.xlsx',  'accutech-ddp', 'Mar 2026'),
    # ACCU-TECH main format (KRAMER- with dash distinguishes from DDP files)
    ('**/ACCU*TECH*KRAMER-*JAN*.xlsx', 'accutech', 'Jan 2026'),
    ('**/ACCU*TECH*KRAMER-*FEB*.xlsx', 'accutech', 'Feb 2026'),
    ('**/ACCU*TECH*KRAMER-*MAR*.xlsx', 'accutech', 'Mar 2026'),
    # Anixter — monthly (Americas filter applied inside parser)
    ('**/Anixter*Jan*.xlsx',        'anixter-americas', 'Jan 2026'),
    ('**/ANIXTER*February*.xlsx',   'anixter-americas', 'Feb 2026'),
    ('**/ANIXTER*March*.xlsx',      'anixter-americas', 'Mar 2026'),
    ('**/ANIXTER*April*.xlsx',      'anixter-americas', 'Apr 2026'),
    ('**/ANIXTER*May*.xlsx',        'anixter-americas', 'May 2026'),
    # NOTE: Consolidated/summary files are EXCLUDED — only original distributor files are imported.
    # Blocked: "Distribution*", "January 2026 POS Reports*", "March 2026 Monthly*",
    #          "POS ADI GLOBAL*AGREGAR*", "1. POS*", "2. POS*", "3. POS*", "4. POS*"
]


class Command(BaseCommand):
    help = 'Import Americas POS files from the From Karina OneDrive folder'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Re-import even if already imported')

    def handle(self, *args, **options):
        force = options['force']
        if not os.path.isdir(KARINA_DIR):
            self.stdout.write(self.style.ERROR(f'Karina folder not found: {KARINA_DIR}'))
            return

        seen_files = set()

        for pattern, parser_code, period in MANIFEST:
            matches = _find(pattern)
            if not matches:
                self.stdout.write(self.style.WARNING(f'  NO MATCH  {pattern}'))
                continue

            for filepath in matches:
                fname = os.path.basename(filepath)
                if fname in seen_files:
                    continue
                seen_files.add(fname)

                self.stdout.write(f'\n  {fname}  [{parser_code}]')

                parser_fn = get_parser(parser_code)
                try:
                    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
                    all_records = parser_fn(wb)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'    ERROR reading file: {e}'))
                    continue

                if not all_records:
                    self.stdout.write(self.style.WARNING('    No records parsed'))
                    continue

                # Normalize country names
                for rec in all_records:
                    if rec.get('country'):
                        rec['country'] = normalize_country(rec['country'])

                # Group by vendor
                by_vendor = defaultdict(list)
                for rec in all_records:
                    vendor = rec.get('vendor', '').strip() or 'Unknown'
                    by_vendor[vendor].append(rec)

                for vendor_name, records in by_vendor.items():
                    dist = _get_or_create_dist(vendor_name)

                    if not force and dist.records.filter(
                        upload__original_filename=fname
                    ).exists():
                        self.stdout.write(
                            f'    SKIP {vendor_name} — already imported (--force to redo)'
                        )
                        continue

                    # Remove existing records for this file+distributor
                    dist.uploads.filter(original_filename=fname).delete()

                    upload = POSUpload.objects.create(
                        distributor=dist,
                        original_filename=fname,
                        report_period=period,
                        row_count=len(records),
                    )
                    POSRecord.objects.bulk_create([
                        POSRecord(upload=upload, distributor=dist, **r)
                        for r in records
                    ])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'    OK  {vendor_name} — {len(records)} records'
                        )
                    )

        self.stdout.write(self.style.SUCCESS('\nAmericas import complete.'))
        self.stdout.write('Refreshing monthly exchange rates...')
        call_command('update_monthly_rates', stdout=self.stdout)
