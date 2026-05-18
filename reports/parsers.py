"""
Excel parsers for each distributor format.
Each parser receives an open openpyxl workbook and returns a list of dicts
matching POSRecord field names.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def _to_str(val):
    if val is None:
        return ''
    return str(val).strip()


def _to_decimal(val):
    if val is None:
        return None
    try:
        return Decimal(str(val).strip())
    except (InvalidOperation, ValueError):
        return None


def _to_int(val):
    if val is None:
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def _to_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s:
        return None
    # Month-only: "2026/01" or "2026-01"
    if re.match(r'^\d{4}[/-]\d{1,2}$', s):
        try:
            return datetime.strptime(s.replace('/', '-') + '-01', '%Y-%m-%d').date()
        except ValueError:
            return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    if ' ' in s:
        try:
            return datetime.strptime(s.split(' ')[0], '%Y-%m-%d').date()
        except ValueError:
            pass
    return None


def _to_post_code(val):
    if val is None:
        return ''
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s if s not in ('0', '') else ''


def _normalize_id(val):
    if val is None:
        return ''
    s = str(val).strip()
    if s.upper() in ('NA', 'N/A', '-', 'NONE', ''):
        return ''
    return s


def _strip_kramer_prefix(val):
    s = _to_str(val)
    if s.upper().startswith('KRAMER '):
        s = s[7:].strip()
    return s


def _is_non_ascii(row):
    return any(
        v is not None and isinstance(v, str) and any(ord(c) > 127 for c in v)
        for v in row
    )


def _is_header_row(row):
    col_a = str(row[0] if row else '').strip().lower()
    col_b = str(row[1] if len(row) > 1 else '').strip().lower()
    return col_a in ('line', 'no.') or 'distributor' in col_b


# ---------------------------------------------------------------------------
# CDEV parser (26-column French format)
# ---------------------------------------------------------------------------

CDEV_COLUMNS = [
    'product_level_1', 'product_level_2', 'product_level_3',
    'item_number', 'brand', 'product_name', 'manufacturer_part_no',
    'product_description', 'sales_price', 'order_ref', 'vendor',
    'quantity', 'invoiced_value', 'currency', 'invoice_date',
    'invoice_ref', 'sda_number', 'special_bid_number',
    'customer_account', 'customer_name', 'address_street',
    'address_city', 'address_county', 'country', 'post_code', 'telephone',
]

_CDEV_DECIMAL = {'sales_price', 'invoiced_value'}
_CDEV_INT = {'quantity'}
_CDEV_DATE = {'invoice_date'}
_CDEV_POST = {'post_code'}


def parse_cdev(wb):
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        record = {}
        for i, field in enumerate(CDEV_COLUMNS):
            val = row[i] if i < len(row) else None
            if field in _CDEV_DECIMAL:
                record[field] = _to_decimal(val)
            elif field in _CDEV_INT:
                record[field] = _to_int(val)
            elif field in _CDEV_DATE:
                record[field] = _to_date(val)
            elif field in _CDEV_POST:
                record[field] = _to_post_code(val)
            else:
                record[field] = _to_str(val)
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# Standard Kramer template parser (13-column, multi-sheet)
# Used by all APAC regional files.
# Column mapping:
#   A=Line  B=Distributor No.  C=Distributor Name  D=Sold-to ID
#   E=Sold-to Name  F=Sold-to Country  G=Sold-to State/Region
#   H=Sold-to Post Code  I=Sold-to Date  J=Part Number
#   K=Quantity  L=Unit_Price ($)  M=Total Price ($)
# ---------------------------------------------------------------------------

def parse_standard_kramer(wb):
    records = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=2, values_only=True):
            if all(v is None for v in row):
                continue
            if _is_non_ascii(row):
                continue
            if _is_header_row(row):
                continue

            def g(i):
                return row[i] if i < len(row) else None

            record = {
                'order_ref':        _to_str(g(1)),
                'vendor':           _to_str(g(2)),
                'customer_account': _normalize_id(g(3)),
                'customer_name':    _to_str(g(4)),
                'country':          _to_str(g(5))[:100],
                'address_county':   _to_str(g(6)),
                'post_code':        _to_post_code(g(7)),
                'invoice_date':     _to_date(g(8)),
                'manufacturer_part_no': _strip_kramer_prefix(g(9)),
                'quantity':         _to_int(g(10)),
                'sales_price':      _to_decimal(g(11)),
                'invoiced_value':   _to_decimal(g(12)),
                'currency':         'USD',
            }
            records.append(record)
    return records


# ---------------------------------------------------------------------------
# Registry: maps distributor code → parser function
# ---------------------------------------------------------------------------

PARSERS = {
    'cdev':           parse_cdev,
    'asean':          parse_standard_kramer,
    'greater-china':  parse_standard_kramer,
    'northeast-asia': parse_standard_kramer,
    'oceania':        parse_standard_kramer,
    'saarc':          parse_standard_kramer,
}


def get_parser(distributor_code):
    return PARSERS.get(distributor_code.lower())
