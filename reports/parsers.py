"""
Excel parsers for each distributor format.
Each parser receives an open openpyxl worksheet and returns a list of dicts
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
        return Decimal(str(val))
    except InvalidOperation:
        return None


def _to_int(val):
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _to_date(val):
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(s[:len(fmt.replace('%Y','YYYY').replace('%m','MM').replace('%d','DD'))], fmt).date()
        except ValueError:
            continue
    # Try stripping anything after the space
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
    # Remove .0 from numeric post codes
    if s.endswith('.0'):
        s = s[:-2]
    return s if s != '0' else ''


# ---------------------------------------------------------------------------
# CDEV parser
# Column order matches the file header exactly.
# ---------------------------------------------------------------------------

CDEV_COLUMNS = [
    'product_level_1',    # A
    'product_level_2',    # B
    'product_level_3',    # C
    'item_number',        # D
    'brand',              # E
    'product_name',       # F
    'manufacturer_part_no',  # G
    'product_description',   # H
    'sales_price',        # I
    'order_ref',          # J
    'vendor',             # K
    'quantity',           # L
    'invoiced_value',     # M
    'currency',           # N
    'invoice_date',       # O
    'invoice_ref',        # P
    'sda_number',         # Q
    'special_bid_number', # R
    'customer_account',   # S
    'customer_name',      # T
    'address_street',     # U
    'address_city',       # V
    'address_county',     # W
    'country',            # X
    'post_code',          # Y
    'telephone',          # Z
]

DECIMAL_FIELDS = {'sales_price', 'invoiced_value'}
INT_FIELDS = {'quantity'}
DATE_FIELDS = {'invoice_date'}
POST_CODE_FIELDS = {'post_code'}


def parse_cdev(worksheet):
    """Parse a CDEV-format worksheet. Returns list of field dicts."""
    records = []
    for row in worksheet.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        record = {}
        for i, field in enumerate(CDEV_COLUMNS):
            val = row[i] if i < len(row) else None
            if field in DECIMAL_FIELDS:
                record[field] = _to_decimal(val)
            elif field in INT_FIELDS:
                record[field] = _to_int(val)
            elif field in DATE_FIELDS:
                record[field] = _to_date(val)
            elif field in POST_CODE_FIELDS:
                record[field] = _to_post_code(val)
            else:
                record[field] = _to_str(val)
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# Registry: maps distributor code → parser function
# Add new distributors here as their formats are mapped.
# ---------------------------------------------------------------------------

PARSERS = {
    'cdev': parse_cdev,
}


def get_parser(distributor_code):
    """Return the parser function for a distributor, or None if not found."""
    return PARSERS.get(distributor_code.lower())
