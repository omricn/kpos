import base64
import json
import os
import urllib.error
import urllib.request
from urllib.parse import quote

from django.core.management.base import BaseCommand

from reports.models import Distributor, PriorityCustomer, PriorityProduct, PrioritySalesperson

PRIORITY_ROOT = 'https://api22.kramerav.com/odata/Priority/tabula.ini/'
# Priority ERP token — supplied via the PRIORITY_API_TOKEN env var (format: "<TOKEN>:PAT").
# Placeholder default keeps real credentials out of source control.
PRIORITY_TOKEN = os.environ.get('PRIORITY_API_TOKEN', 'REPLACE_WITH_PRIORITY_TOKEN:PAT')
PRIORITY_AUTH = base64.b64encode(PRIORITY_TOKEN.encode()).decode()
PAGE_SIZE = 2000

# All Priority companies accessible via the API (ktech and kkorea return 400).
PRIORITY_COMPANIES = [
    'krmel', 'kaus', 'kcanada', 'kchile', 'chin', 'germany', 'khongk',
    'india', 'kmexi', 'knewz', 'kuk', 'kca', 'kemea', 'ashb',
    'sngpr', 'krmfr', 'ksweden', 'kusa21', 'kusmnt', 'krmnt',
    'wowind', 'wowsing', 'zvusa', 'zvger',
]


def _get(path, company='krmel'):
    # Encode unsafe chars (e.g. spaces in part numbers) while preserving OData syntax
    url = PRIORITY_ROOT + company + '/' + quote(path, safe="?$=&,();':@/")
    req = urllib.request.Request(
        url,
        headers={'Authorization': f'Basic {PRIORITY_AUTH}', 'Accept': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _get_all(entity, select, extra='', company='krmel'):
    """Fetch all rows from a Priority entity, handling 2000-row pagination."""
    rows = []
    skip = 0
    while True:
        path = f'{entity}?$top={PAGE_SIZE}&$skip={skip}&$select={select}'
        if extra:
            path += f'&{extra}'
        data = _get(path, company=company)
        page = data.get('value', [])
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
    return rows


class Command(BaseCommand):
    help = 'Sync product catalog, salesperson, and customer data from Priority ERP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products-only', action='store_true',
            help='Only sync the product catalog (LOGPART)',
        )
        parser.add_argument(
            '--agents-only', action='store_true',
            help='Only sync salesperson data (AGENTS + distributor mapping)',
        )
        parser.add_argument(
            '--customers-only', action='store_true',
            help='Only sync customer data (CUSTOMERS — active, all companies)',
        )

    def handle(self, *args, **options):
        products_only  = options['products_only']
        agents_only    = options['agents_only']
        customers_only = options['customers_only']

        # If a specific --*-only flag is set, run only that section.
        # With no flag, run everything.
        run_products  = not agents_only  and not customers_only
        run_agents    = not products_only and not customers_only
        run_customers = not products_only and not agents_only

        if products_only:
            run_products = True
        if agents_only:
            run_agents = True
        if customers_only:
            run_customers = True

        if run_products:
            self._sync_products()
        if run_agents:
            self._sync_agents()
            self._sync_distributor_salespersons()
        if run_customers:
            self._sync_customers()

    def _sync_products(self):
        """
        Sync only the Kramer part numbers we actually have in KPos — individual key lookups
        are ~1s each vs 55s per 100 rows for a full LOGPART table scan.
        """
        from reports.models import POSRecord
        self.stdout.write('Syncing Priority product catalog (LOGPART — known parts only)…')

        part_numbers = list(
            POSRecord.objects.exclude(manufacturer_part_no='')
            .order_by()
            .values_list('manufacturer_part_no', flat=True)
            .distinct()
        )
        if not part_numbers:
            self.stdout.write('  No part numbers in KPos — nothing to sync.')
            return

        existing = set(PriorityProduct.objects.values_list('part_number', flat=True))
        to_fetch = part_numbers  # always refresh all so descriptions stay current

        self.stdout.write(f'  Fetching {len(to_fetch)} part numbers from Priority…')
        created = updated = missing = errors = 0

        for part in to_fetch:
            try:
                row = _get(f'LOGPART({part!r})?$select=PARTNAME,PARTDES,EPARTDES,FAMILYNAME,FAMILYDES,STATDES')
                obj, is_new = PriorityProduct.objects.update_or_create(
                    part_number=part,
                    defaults={
                        'description':        (row.get('EPARTDES') or '').strip(),
                        'description_local':  (row.get('PARTDES') or '').strip(),
                        'family':             (row.get('FAMILYNAME') or '').strip(),
                        'family_description': (row.get('FAMILYDES') or '').strip(),
                        'status':             (row.get('STATDES') or '').strip(),
                    },
                )
                if is_new:
                    created += 1
                else:
                    updated += 1
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    missing += 1
                else:
                    self.stderr.write(self.style.WARNING(f'  {part}: HTTP {e.code}'))
                    errors += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  {part}: {e}'))
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Products: {created} created, {updated} updated, '
            f'{missing} not in Priority, {errors} errors'
        ))

    def _sync_agents(self):
        self.stdout.write('Syncing Priority salespersons (AGENTS)…')
        try:
            rows = _get_all('AGENTS', 'AGENTCODE,AGENTNAME,EAGENTNAME')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'  Failed: {e}'))
            return

        created = updated = 0
        for row in rows:
            code = row.get('AGENTCODE', '').strip()
            if not code:
                continue
            # Prefer English name if available
            name = (row.get('EAGENTNAME') or row.get('AGENTNAME') or '').strip()
            obj, is_new = PrioritySalesperson.objects.update_or_create(
                agent_code=code,
                defaults={'agent_name': name},
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Salespersons: {created} created, {updated} updated ({created + updated} total)'
        ))

    def _sync_distributor_salespersons(self):
        self.stdout.write('Syncing distributor → salesperson mapping (CUSTOMERS)…')
        dists = Distributor.objects.exclude(priority_customer_code='')
        if not dists.exists():
            self.stdout.write('  No distributors have priority_customer_code set — skipping.')
            self.stdout.write('  Set priority_customer_code in Django admin for each distributor, then re-run.')
            return

        for dist in dists:
            code = dist.priority_customer_code.strip()
            # Determine which Priority company this distributor lives in
            company = dist.priority_company if hasattr(dist, 'priority_company') and dist.priority_company else 'krmel'
            try:
                data = _get(
                    f'CUSTOMERS({code!r})?$select=CUSTNAME,CUSTDES,AGENTCODE,AGENTNAME,STATDES',
                    company=company,
                )
                agent_code = (data.get('AGENTCODE') or '').strip()
                agent_name = (data.get('AGENTNAME') or '').strip()
                dist.salesperson_code = agent_code
                dist.salesperson_name = agent_name
                dist.save(update_fields=['salesperson_code', 'salesperson_name'])
                self.stdout.write(self.style.SUCCESS(
                    f'  {dist.name}: salesperson = {agent_code} ({agent_name})'
                ))
            except urllib.error.HTTPError as e:
                self.stderr.write(self.style.WARNING(
                    f'  {dist.name} (code={code!r}): HTTP {e.code} — check priority_customer_code'
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  {dist.name}: {e}'))

    def _sync_customers(self):
        """Sync active customers from all Priority companies into PriorityCustomer."""
        self.stdout.write('Syncing Priority customers (CUSTOMERS — Active only, all companies)…')
        total_created = total_updated = total_skipped = 0

        for company in PRIORITY_COMPANIES:
            try:
                rows = _get_all(
                    'CUSTOMERS',
                    'CUSTNAME,CUSTDES,AGENTCODE,AGENTNAME,STATDES',
                    extra="$filter=STATDES eq 'Active'",
                    company=company,
                )
            except urllib.error.HTTPError as e:
                self.stderr.write(self.style.WARNING(f'  {company}: HTTP {e.code} — skipping'))
                total_skipped += 1
                continue
            except Exception as e:
                self.stderr.write(self.style.WARNING(f'  {company}: {e} — skipping'))
                total_skipped += 1
                continue

            created = updated = 0
            for row in rows:
                code = (row.get('CUSTNAME') or '').strip()
                if not code:
                    continue
                _, is_new = PriorityCustomer.objects.update_or_create(
                    custname=code,
                    company=company,
                    defaults={
                        'custdes':    (row.get('CUSTDES')    or '').strip(),
                        'agent_code': (row.get('AGENTCODE')  or '').strip(),
                        'agent_name': (row.get('AGENTNAME')  or '').strip(),
                        'status':     (row.get('STATDES')    or '').strip(),
                    },
                )
                if is_new:
                    created += 1
                else:
                    updated += 1

            self.stdout.write(self.style.SUCCESS(
                f'  {company}: {created} created, {updated} updated ({created + updated} total)'
            ))
            total_created += created
            total_updated += updated

        self.stdout.write(self.style.SUCCESS(
            f'Customers done: {total_created} created, {total_updated} updated'
            + (f', {total_skipped} companies skipped' if total_skipped else '')
        ))
