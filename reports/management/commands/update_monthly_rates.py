"""
Fetch historical monthly exchange rates from ECB and store in MonthlyRate.

Usage:
  python manage.py update_monthly_rates              # auto-detect range from POSRecord dates
  python manage.py update_monthly_rates --start 2026-01 --end 2026-06
"""
import csv
import io
import urllib.request
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db.models import Min, Max

from reports.models import POSRecord, MonthlyRate


ECB_URL = (
    'https://data-api.ecb.europa.eu/service/data/EXR/'
    'M.USD+GBP+SEK+DKK.EUR.SP00.A'
    '?format=csvdata&startPeriod={start}&endPeriod={end}'
)


class Command(BaseCommand):
    help = 'Fetch historical monthly FX rates from ECB and populate MonthlyRate table'

    def add_arguments(self, parser):
        parser.add_argument('--start', help='Start period YYYY-MM (default: earliest invoice month)')
        parser.add_argument('--end', help='End period YYYY-MM (default: latest invoice month)')

    def handle(self, *args, **options):
        # Determine date range
        if options['start'] and options['end']:
            start = options['start']
            end = options['end']
        else:
            bounds = POSRecord.objects.aggregate(mn=Min('invoice_date'), mx=Max('invoice_date'))
            if not bounds['mn']:
                self.stdout.write(self.style.ERROR('No POSRecord data found'))
                return
            start = bounds['mn'].strftime('%Y-%m')
            end = bounds['mx'].strftime('%Y-%m')

        self.stdout.write(f'Fetching ECB rates {start} → {end}')

        url = ECB_URL.format(start=start, end=end)
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                content = r.read().decode('utf-8')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ECB API error: {e}'))
            return

        # Parse CSV — ECB gives X units of currency per 1 EUR
        # Columns: KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,...
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)
        col = {h: i for i, h in enumerate(headers)}

        # Collect {period: {currency: x_per_eur}}
        raw = {}
        for row in reader:
            if len(row) <= col['OBS_VALUE']:
                continue
            period = row[col['TIME_PERIOD']]  # e.g. "2026-01"
            currency = row[col['CURRENCY']]   # e.g. "USD"
            try:
                value = Decimal(row[col['OBS_VALUE']])
            except (InvalidOperation, IndexError):
                continue
            raw.setdefault(period, {})[currency] = value

        created = updated = 0
        for period, fx in sorted(raw.items()):
            year, month = int(period[:4]), int(period[5:7])
            usd_per_eur = fx.get('USD')
            if not usd_per_eur:
                continue

            # Rates for each currency: 1 unit of that currency = ? USD / ? EUR
            entries = {
                'USD': (Decimal('1'), Decimal('1') / usd_per_eur),
                'EUR': (usd_per_eur, Decimal('1')),
            }
            for cur in ('GBP', 'SEK', 'DKK'):
                x_per_eur = fx.get(cur)
                if x_per_eur:
                    entries[cur] = (usd_per_eur / x_per_eur, Decimal('1') / x_per_eur)

            for currency, (rate_usd, rate_eur) in entries.items():
                obj, was_created = MonthlyRate.objects.update_or_create(
                    year=year, month=month, currency=currency,
                    defaults={'rate_to_usd': rate_usd, 'rate_to_eur': rate_eur},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {created} created, {updated} updated across {len(raw)} months'
        ))
