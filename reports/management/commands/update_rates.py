import json
import urllib.request
from decimal import Decimal

from django.core.management.base import BaseCommand

from reports.models import ExchangeRate


class Command(BaseCommand):
    help = 'Fetch latest exchange rates from frankfurter.app and update the database'

    def handle(self, *args, **options):
        url = 'https://open.er-api.com/v6/latest/USD'
        self.stdout.write(f'Fetching rates from {url} ...')

        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to fetch rates: {e}'))
            return

        api_rates = data['rates']  # {EUR: X, GBP: X, SEK: X, DKK: X, ...} — all per 1 USD

        # Build {currency: (rate_to_usd, rate_to_eur)}
        eur_per_usd = Decimal(str(api_rates['EUR']))
        entries = {
            'USD': (Decimal('1'), eur_per_usd),
            'EUR': (Decimal('1') / eur_per_usd, Decimal('1')),
            'GBP': (Decimal('1') / Decimal(str(api_rates['GBP'])),
                    eur_per_usd / Decimal(str(api_rates['GBP']))),
            'SEK': (Decimal('1') / Decimal(str(api_rates['SEK'])),
                    eur_per_usd / Decimal(str(api_rates['SEK']))),
            'DKK': (Decimal('1') / Decimal(str(api_rates['DKK'])),
                    eur_per_usd / Decimal(str(api_rates['DKK']))),
        }

        for cur, (r_usd, r_eur) in entries.items():
            obj, created = ExchangeRate.objects.update_or_create(
                currency=cur,
                defaults={'rate_to_usd': r_usd, 'rate_to_eur': r_eur},
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{action} {cur}: 1 {cur} = ${float(r_usd):.6f} USD / €{float(r_eur):.6f} EUR'
                )
            )

        self.stdout.write(self.style.SUCCESS('Exchange rates updated successfully.'))
