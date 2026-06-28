"""
Management command to search Priority CUSTOMERS by name fragment.

Usage:
    python manage.py find_priority_customer starin
    python manage.py find_priority_customer midwich
    python manage.py find_priority_customer --list-all

Since Priority doesn't support contains() filtering, this command pages through
all customers locally and prints matches. Use it to find the CUSTNAME code
to set on each KPos Distributor in Django admin.
"""
import base64
import json
import os
import urllib.request
from urllib.parse import quote

from django.core.management.base import BaseCommand

PRIORITY_BASE = 'https://api22.kramerav.com/odata/Priority/tabula.ini/krmel/'
# Priority ERP token — supplied via the PRIORITY_API_TOKEN env var (format: "<TOKEN>:PAT").
# Placeholder default keeps real credentials out of source control.
PRIORITY_TOKEN = os.environ.get('PRIORITY_API_TOKEN', 'REPLACE_WITH_PRIORITY_TOKEN:PAT')
PRIORITY_AUTH = base64.b64encode(PRIORITY_TOKEN.encode()).decode()
PAGE_SIZE = 2000


class Command(BaseCommand):
    help = 'Search Priority CUSTOMERS by name to find the CUSTNAME code for a distributor'

    def add_arguments(self, parser):
        parser.add_argument('search', nargs='?', default='', help='Name fragment to search for (case-insensitive)')
        parser.add_argument('--list-all', action='store_true', help='List all active customers')
        parser.add_argument('--active-only', action='store_true', default=True, help='Only show active customers')

    def handle(self, *args, **options):
        search = options['search'].lower().strip()
        list_all = options['list_all']

        if not search and not list_all:
            self.stdout.write(self.style.WARNING(
                'Usage: python manage.py find_priority_customer <name_fragment>\n'
                'Example: python manage.py find_priority_customer starin'
            ))
            return

        self.stdout.write(f'Searching Priority CUSTOMERS{"" if not search else f" for \"{search}\""}…')
        self.stdout.write('(Paging through all customers — may take a few minutes)\n')

        skip = 0
        total_seen = 0
        matches = []

        while True:
            path = (
                f'CUSTOMERS?$top={PAGE_SIZE}&$skip={skip}'
                f'&$select=CUSTNAME,CUSTDES,ECUSTDES,AGENTCODE,AGENTNAME,STATDES'
            )
            url = PRIORITY_BASE + quote(path, safe="?$=&,();':@/")
            req = urllib.request.Request(
                url,
                headers={'Authorization': f'Basic {PRIORITY_AUTH}', 'Accept': 'application/json'},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read())
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed at skip={skip}: {e}'))
                break

            page = data.get('value', [])
            if not page:
                break

            for row in page:
                cdes = (row.get('ECUSTDES') or row.get('CUSTDES') or '').strip()
                custname = row.get('CUSTNAME', '')
                status = row.get('STATDES', '')

                if options['active_only'] and status != 'Active':
                    continue
                if not list_all and search and search not in cdes.lower() and search not in custname.lower():
                    continue
                matches.append({
                    'custname': custname,
                    'cdes': cdes,
                    'agent_code': row.get('AGENTCODE', ''),
                    'agent_name': row.get('AGENTNAME', ''),
                    'status': status,
                })

            total_seen += len(page)
            self.stdout.write(f'  Scanned {total_seen} customers, {len(matches)} matches so far…')

            if len(page) < PAGE_SIZE:
                break
            skip += PAGE_SIZE

        self.stdout.write()
        if not matches:
            self.stdout.write(self.style.WARNING(f'No matches found for "{search}".'))
            return

        self.stdout.write(self.style.SUCCESS(f'{len(matches)} match(es):\n'))
        self.stdout.write(f'{"CUSTNAME":15} {"Name":50} {"Agent":12} {"Agent Name"}')
        self.stdout.write('-' * 100)
        for m in sorted(matches, key=lambda x: x['cdes']):
            self.stdout.write(
                f'{m["custname"]:15} {m["cdes"][:50]:50} {m["agent_code"]:12} {m["agent_name"]}'
            )

        self.stdout.write(
            f'\nTo link a distributor: go to Admin → Distributors → [distributor name] → '
            f'set "Priority customer code" to the CUSTNAME value above, then run:\n'
            f'  python manage.py sync_priority --agents-only'
        )
