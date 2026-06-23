"""
Composite sync command — runs all Priority ERP + exchange rate syncs in sequence.
Intended to be called by the Azure Container Apps scheduled Job (runs daily).
Safe to re-run manually at any time; all operations are idempotent.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run all Priority ERP + exchange rate syncs (products, salespersons, distributor mapping, rates)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-products', action='store_true',
            help='Skip product catalog sync (faster if only reps/rates changed)',
        )
        parser.add_argument(
            '--skip-rates', action='store_true',
            help='Skip exchange rate updates',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== KPOS Full Sync ==='))

        if not options['skip_products']:
            self.stdout.write(self.style.MIGRATE_HEADING('\n[1/4] Products + Salespersons (sync_priority)'))
            call_command('sync_priority')
        else:
            self.stdout.write(self.style.MIGRATE_HEADING('\n[1/4] Skipping products — syncing salespersons only'))
            call_command('sync_priority', agents_only=True)

        self.stdout.write(self.style.MIGRATE_HEADING('\n[2/4] Current exchange rates (update_rates)'))
        call_command('update_rates')

        self.stdout.write(self.style.MIGRATE_HEADING('\n[3/4] Historical monthly rates (update_monthly_rates)'))
        call_command('update_monthly_rates')

        self.stdout.write(self.style.SUCCESS('\n=== Sync complete ==='))
