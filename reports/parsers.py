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
    # 8-char compact form YYYYMMDD (e.g. ALSO FI: '20260107')
    if re.match(r'^\d{8}$', s):
        try:
            return datetime.strptime(s, '%Y%m%d').date()
        except ValueError:
            pass
    # 2-digit year DD/MM/YY (e.g. Kramer EMEA format: '09/03/26')
    if re.match(r'^\d{2}/\d{2}/\d{2}$', s):
        try:
            return datetime.strptime(s, '%d/%m/%y').date()
        except ValueError:
            pass
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d',
                '%m-%d-%Y', '%d-%m-%Y'):
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


def _to_date_us(val):
    """Date parser for US-format files (MM/DD/YYYY takes priority over DD/MM/YYYY)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
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


def _g(row, i):
    """Safe column accessor."""
    return row[i] if i < len(row) else None


# ---------------------------------------------------------------------------
# Nordic multi-sheet (Copy of Direct and Disti Sales 2026.xlsx)
# Sheets: Captech | Netsmart | F9 | ALSO FI | Fineman
# Each sheet = one EMEA distributor; customer column = reseller/end-buyer.
# ---------------------------------------------------------------------------

def _parse_captech_sheet(ws, vendor):
    # Cols: 0=Part No, 1=Description, 2=Qty, 3=Invoice Date, 4=Price/Unit,
    #       5=Currency, 6=Shipto Corp ID, 7=Shipto Dist Name (customer),
    #       8=Street1, 9=Street2, 10=City, 11=Post Code, 12=Country Code,
    #       13=Cost(SEK), 14=Total(SEK)
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        street = ' '.join(filter(None, [_to_str(_g(row, 8)), _to_str(_g(row, 9))]))
        records.append({
            'vendor':               vendor,
            'manufacturer_part_no': _to_str(_g(row, 0)),
            'product_description':  _strip_kramer_prefix(_g(row, 1)),
            'quantity':             _to_int(_g(row, 2)),
            'invoice_date':         _to_date(_g(row, 3)),
            'sales_price':          _to_decimal(_g(row, 4)),
            'currency':             _to_str(_g(row, 5)) or 'SEK',
            'customer_account':     _to_str(_g(row, 6)),
            'customer_name':        _to_str(_g(row, 7)),
            'address_street':       street,
            'address_city':         _to_str(_g(row, 10)),
            'post_code':            _to_post_code(_g(row, 11)),
            'country':              _to_str(_g(row, 12)),
            'invoiced_value':       _to_decimal(_g(row, 14)),
        })
    return records


def _parse_netsmart_sheet(ws, vendor):
    # Swedish headers — Cols: 0=Ursprung, 1=Ordernr, 2=Artikelkod (part),
    # 3=Benämning (desc), 4=Fakturadatum (date), 5=Lev.datum, 6=Antal (qty),
    # 7=Leveransadress 1 (customer), 8=Addr2 (street), 9=Addr3 (postcode city),
    # 10=Kostnad (cost)
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        addr3 = _to_str(_g(row, 9))
        parts = addr3.rsplit(None, 1)
        city = parts[1] if len(parts) > 1 else addr3
        post_code = parts[0].strip() if len(parts) > 1 else ''
        records.append({
            'vendor':               vendor,
            'order_ref':            _to_str(_g(row, 1)),
            'manufacturer_part_no': _to_str(_g(row, 2)),
            'product_description':  _strip_kramer_prefix(_g(row, 3)),
            'invoice_date':         _to_date(_g(row, 4)),
            'quantity':             _to_int(_g(row, 6)),
            'customer_name':        _to_str(_g(row, 7)),
            'address_street':       _to_str(_g(row, 8)),
            'address_city':         city,
            'post_code':            post_code,
            'invoiced_value':       _to_decimal(_g(row, 10)),
            'currency':             'SEK',
        })
    return records


def _parse_f9_sheet(ws, vendor):
    # Cols: 0=Partner (customer), 1=Product group, 2=SKU, 3=Description,
    # 4=Delivery customer (same as Partner), 5=Delivery addr, 6=Delivery city,
    # 7=Country, 8=Invoice date, 9=Sold qty (empty), 10=BidRef (holds qty),
    # 11=Sold cost
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        records.append({
            'vendor':               vendor,
            'product_level_1':      _to_str(_g(row, 1)),
            'manufacturer_part_no': _to_str(_g(row, 2)),
            'product_description':  _strip_kramer_prefix(_g(row, 3)),
            'customer_name':        _to_str(_g(row, 4)),
            'address_street':       _to_str(_g(row, 5)),
            'address_city':         _to_str(_g(row, 6)),
            'country':              _to_str(_g(row, 7)),
            'invoice_date':         _to_date(_g(row, 8)),
            'quantity':             _to_int(_g(row, 10)),  # "BidRef" col holds qty
            'invoiced_value':       _to_decimal(_g(row, 11)),
            'currency':             'EUR',
        })
    return records


def _parse_also_fi_sheet(ws, vendor):
    # Cols: 0=DATE (YYYYMMDD), 1=ALSO MATERIAL, 2=MFR MATERIAL, 3=EAN,
    # 4=MATERIAL DESCRIPTION, 5=CUSTOMER NUMBER, 6=CUSTOMER NAME,
    # 7=CUSTOMER STREET, 8=CUSTOMER ZIP, 9=CUSTOMER CITY, 10=CUSTOMER COUNTRY,
    # 11=QTY, 12=PURCHASE PRICE, 13=CURRENCY, 14=CUSTOMER VAT, 15=TOTAL EUR
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        records.append({
            'vendor':               vendor,
            'invoice_date':         _to_date(_g(row, 0)),
            'item_number':          _to_str(_g(row, 1)),
            'manufacturer_part_no': _to_str(_g(row, 2)),
            'product_description':  _strip_kramer_prefix(_g(row, 4)),
            'customer_account':     _to_str(_g(row, 5)),
            'customer_name':        _to_str(_g(row, 6)),
            'address_street':       _to_str(_g(row, 7)),
            'post_code':            _to_post_code(_g(row, 8)),
            'address_city':         _to_str(_g(row, 9)),
            'country':              _to_str(_g(row, 10)),
            'quantity':             _to_int(_g(row, 11)),
            'sales_price':          _to_decimal(_g(row, 12)),
            'currency':             _to_str(_g(row, 13)) or 'EUR',
            'invoiced_value':       _to_decimal(_g(row, 15)),
        })
    return records


def _parse_fineman_sheet(ws, vendor):
    # Cols: 0=Datum, 1=No_Item (part), 2=Description_Item, 3=UoM,
    # 4=SourceNo (customer acct), 5=CustName, 6=InvQty, 7=SalesAmt,
    # 8=Profit, 9=DiscountAmount, 10=ProfitPct
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        records.append({
            'vendor':               vendor,
            'invoice_date':         _to_date(_g(row, 0)),
            'manufacturer_part_no': _to_str(_g(row, 1)),
            'product_description':  _strip_kramer_prefix(_g(row, 2)),
            'customer_account':     _to_str(_g(row, 4)),
            'customer_name':        _to_str(_g(row, 5)),
            'quantity':             _to_int(_g(row, 6)),
            'invoiced_value':       _to_decimal(_g(row, 7)),
            'currency':             'DKK',
        })
    return records


def parse_nordic_multi_sheet(wb):
    """
    'Copy of Direct and Disti Sales 2026.xlsx' — one sheet per distributor.
    Returns all records with vendor = sheet name.
    """
    _handlers = {
        'Captech':  (_parse_captech_sheet,  'EXERTIS CAPTECH AB'),
        'Netsmart': (_parse_netsmart_sheet, 'Netsmart AB'),
        'F9':       (_parse_f9_sheet,       'F9 DISTRIBUTION OY'),
        'ALSO FI':  (_parse_also_fi_sheet,  'ALSO FINLAND OY'),
        'Fineman':  (_parse_fineman_sheet,  'FINEMAN A/S'),
    }
    records = []
    for ws in wb.worksheets:
        entry = _handlers.get(ws.title.strip())
        if entry:
            handler, full_name = entry
            records.extend(handler(ws, vendor=full_name))
    return records


# ---------------------------------------------------------------------------
# Midwich UK — "Kramer and ZeeVee sales.xlsx"
# Cols: 0=Division, 1=Product Group, 2=MIDW Part No, 3=Mfr Part No,
#       4=Order Ref, 5=Customer Account, 6=Distributer Name (end customer),
#       7=Invoiced Value, 8=Quantity, 9=Invoice Date
# ---------------------------------------------------------------------------

def parse_midwich_zeevee(wb):
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        records.append({
            'vendor':               'Midwich Limited',
            'product_level_1':      _to_str(_g(row, 1)),
            'item_number':          _to_str(_g(row, 2)),
            'manufacturer_part_no': _to_str(_g(row, 3)),
            'order_ref':            _to_str(_g(row, 4)),
            'customer_account':     _to_str(_g(row, 5)),
            'customer_name':        _to_str(_g(row, 6)),
            'invoiced_value':       _to_decimal(_g(row, 7)),
            'quantity':             _to_int(_g(row, 8)),
            'invoice_date':         _to_date(_g(row, 9)),
            'currency':             'GBP',
        })
    return records


# ---------------------------------------------------------------------------
# EMEA Kramer internal format — "EMEA_POS_DATA_24-26.xlsx"
# Date format: DD/MM/YY  |  Distributor identified by Distributor_No col.
# USD prices available in cols 21-22; used preferentially for consistency.
# Cols: 0=Date, 1=Distributor_No, 2=Zip_Code, 3=Part_Number, 4=Quantity,
#       5=Unit_Price, 7=Country, 8=Total_Price, 9=Partner, 10=Address,
#       17=Part_Description, 19=Transaction_Currency, 21=USD_Unit_Price,
#       22=USD_Total_Price, 30=Sold_To_Customer_Name, 31=Sold_To_Address,
#       32=Sold_To_City, 33=Sold_To_State, 35=Sold_To_Country
# ---------------------------------------------------------------------------

_EMEA_DIST_NAMES = {
    'C-MIDWICHL': 'Midwich',
    'C-ANIXTER':  'Anixter',
    'C-EXERTIS':  'Exertis',
    'C-RGBCOMMU': 'RGB Communications',
}


def parse_emea_kramer_format(wb):
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        dist_no = _to_str(_g(row, 1))
        vendor = _EMEA_DIST_NAMES.get(dist_no, dist_no)
        usd_total = _to_decimal(_g(row, 22))
        usd_unit  = _to_decimal(_g(row, 21))
        if usd_total is not None:
            invoiced_value = usd_total
            sales_price    = usd_unit
            currency       = 'USD'
        else:
            invoiced_value = _to_decimal(_g(row, 8))
            sales_price    = _to_decimal(_g(row, 5))
            currency       = _to_str(_g(row, 19)) or ''
        customer = _to_str(_g(row, 30)) or _to_str(_g(row, 9))
        country  = _to_str(_g(row, 35)) or _to_str(_g(row, 7))
        records.append({
            'vendor':               vendor,
            'invoice_date':         _to_date(_g(row, 0)),
            'manufacturer_part_no': _to_str(_g(row, 3)),
            'product_description':  _to_str(_g(row, 17)),
            'quantity':             _to_int(_g(row, 4)),
            'sales_price':          sales_price,
            'invoiced_value':       invoiced_value,
            'currency':             currency,
            'customer_name':        customer,
            'address_street':       _to_str(_g(row, 31)) or _to_str(_g(row, 10)),
            'address_city':         _to_str(_g(row, 32)),
            'address_county':       _to_str(_g(row, 33)),
            'post_code':            _to_post_code(_g(row, 34)),
            'country':              country,
        })
    return records


# ---------------------------------------------------------------------------
# Bomisco Format — "Kramer_Reports_YYYYMMDD.xlsx"  (sheet: POS Bomisco Format)
# This is the Boomisco-processed EMEA export with proper Distributor_Name,
# extended date range, and USD columns.
# Cols: 0=Date, 2=Distributor_Name, 3=Zip_Code, 4=Part_Number, 5=Quantity,
#       6=Unit_Price, 9=Country, 10=Total_Price, 11=Partner, 12=Address,
#       18=State, 19=Part_Description, 29=Sold_To_Customer_Name,
#       30=Sold_To_Address, 31=Sold_To_City, 32=Sold_To_State,
#       33=Sold_To_Zip_Code, 34=Sold_To_Country,
#       50=Transaction_Currency, 51=USD_Unit_Price, 52=USD_Total_Price
# ---------------------------------------------------------------------------

def parse_bomisco_format(wb):
    ws = wb['POS Bomisco Format']
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        vendor = _to_str(_g(row, 2)) or _to_str(_g(row, 1))
        usd_total = _to_decimal(_g(row, 52))
        usd_unit  = _to_decimal(_g(row, 51))
        if usd_total is not None:
            invoiced_value = usd_total
            sales_price    = usd_unit
            currency       = 'USD'
        else:
            invoiced_value = _to_decimal(_g(row, 10))
            sales_price    = _to_decimal(_g(row, 6))
            currency       = _to_str(_g(row, 50)) or ''
        customer = _to_str(_g(row, 29)) or _to_str(_g(row, 11))
        country  = _to_str(_g(row, 34)) or _to_str(_g(row, 9))
        records.append({
            'vendor':               vendor,
            'invoice_date':         _to_date(_g(row, 0)),
            'manufacturer_part_no': _to_str(_g(row, 4)),
            'product_description':  _to_str(_g(row, 19)),
            'quantity':             _to_int(_g(row, 5)),
            'sales_price':          sales_price,
            'invoiced_value':       invoiced_value,
            'currency':             currency,
            'customer_name':        customer,
            'post_code':            _to_post_code(_g(row, 3)),
            'address_street':       _to_str(_g(row, 30)) or _to_str(_g(row, 12)),
            'address_city':         _to_str(_g(row, 31)),
            'address_county':       _to_str(_g(row, 32)) or _to_str(_g(row, 18)),
            'country':              country,
        })
    return records


# ---------------------------------------------------------------------------
# Country normalization helper (mirrors views.normalize_country)
# ---------------------------------------------------------------------------

_ISO_COUNTRIES = {
    'AF':'Afghanistan','AL':'Albania','DZ':'Algeria','AD':'Andorra','AO':'Angola',
    'AR':'Argentina','AM':'Armenia','AU':'Australia','AT':'Austria','AZ':'Azerbaijan',
    'BS':'Bahamas','BH':'Bahrain','BD':'Bangladesh','BE':'Belgium','BZ':'Belize',
    'BJ':'Benin','BR':'Brazil','BN':'Brunei','BG':'Bulgaria','CA':'Canada',
    'CL':'Chile','CN':'China','CO':'Colombia','CR':'Costa Rica','HR':'Croatia',
    'CY':'Cyprus','CZ':'Czech Republic','DK':'Denmark','DO':'Dominican Republic',
    'EC':'Ecuador','EG':'Egypt','EE':'Estonia','FI':'Finland','FR':'France',
    'GE':'Georgia','DE':'Germany','GH':'Ghana','GR':'Greece','GT':'Guatemala',
    'HN':'Honduras','HK':'Hong Kong','HU':'Hungary','IS':'Iceland','IN':'India',
    'ID':'Indonesia','IR':'Iran','IQ':'Iraq','IE':'Ireland','IL':'Israel',
    'IT':'Italy','JM':'Jamaica','JP':'Japan','JO':'Jordan','KZ':'Kazakhstan',
    'KE':'Kenya','KR':'South Korea','KW':'Kuwait','LV':'Latvia','LB':'Lebanon',
    'LT':'Lithuania','LU':'Luxembourg','MY':'Malaysia','MT':'Malta','MX':'Mexico',
    'MD':'Moldova','MA':'Morocco','MZ':'Mozambique','MM':'Myanmar','NA':'Namibia',
    'NL':'Netherlands','NZ':'New Zealand','NI':'Nicaragua','NG':'Nigeria',
    'NO':'Norway','OM':'Oman','PK':'Pakistan','PA':'Panama','PY':'Paraguay',
    'PE':'Peru','PH':'Philippines','PL':'Poland','PT':'Portugal','QA':'Qatar',
    'RO':'Romania','RU':'Russia','SA':'Saudi Arabia','SN':'Senegal','RS':'Serbia',
    'SG':'Singapore','SK':'Slovakia','SI':'Slovenia','ZA':'South Africa',
    'ES':'Spain','LK':'Sri Lanka','SE':'Sweden','CH':'Switzerland','TW':'Taiwan',
    'TH':'Thailand','TN':'Tunisia','TR':'Turkey','UA':'Ukraine',
    'AE':'United Arab Emirates','GB':'United Kingdom','US':'United States',
    'UY':'Uruguay','UZ':'Uzbekistan','VE':'Venezuela','VN':'Vietnam','YE':'Yemen',
    'ZM':'Zambia','ZW':'Zimbabwe','AW':'Aruba','PR':'Puerto Rico',
    'AX':'Åland Islands','EH':'Western Sahara',
}
_COUNTRY_NAME_MAP = {v.lower(): v for v in _ISO_COUNTRIES.values()}
_COUNTRY_ALIASES = {
    'usa': 'United States', 'united states of america': 'United States',
    'uk': 'United Kingdom', 'great britain': 'United Kingdom',
    'korea': 'South Korea', 'republic of korea': 'South Korea',
    'méxico': 'Mexico', 'mexico peso': 'Mexico',
    'n/a': '', 'na': '', 'none': '',
}


def _normalize_country_str(raw):
    if not raw:
        return raw
    s = raw.strip()
    if not s:
        return s
    up = s.upper()
    if len(s) == 2 and up in _ISO_COUNTRIES:
        return _ISO_COUNTRIES[up]
    lo = s.lower()
    if lo in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[lo]
    if lo in _COUNTRY_NAME_MAP:
        return _COUNTRY_NAME_MAP[lo]
    return s.title() if s.isupper() else s


# ---------------------------------------------------------------------------
# Americas: ALMO (Kramer + ZeeVee, same format)
# Cols: 0=CUSTOMER(ID), 1=NAME, 2=CUST ADDR1, 3=CUST ADDR2, 4=CITY,
#       5=STATE, 6=ZIP, 7=PHONE, 8=QTY SHIPPED, 9=MFG PART, 10=UNIT COST,
#       11=EXTENDED COST, 12=INVOICE DATE, 13=INVOICE NUMBER, 14=END USER NAME,
#       15-19=END USER ADDR, 20=MFR, 21-22=SALES, 23=RESALE, 24=MFG MODEL
# ---------------------------------------------------------------------------

def parse_almo(wb):
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        addr = ' '.join(filter(None, [_to_str(_g(row, 2)), _to_str(_g(row, 3))]))
        records.append({
            'vendor':           'ALMO',
            'customer_account': _to_str(_g(row, 0)),
            'customer_name':    _to_str(_g(row, 1)),
            'address_street':   addr,
            'address_city':     _to_str(_g(row, 4)),
            'address_county':   _to_str(_g(row, 5)),
            'post_code':        _to_post_code(_g(row, 6)),
            'telephone':        _to_str(_g(row, 7)),
            'quantity':         _to_int(_g(row, 8)),
            'manufacturer_part_no': _to_str(_g(row, 9)),
            'sales_price':      _to_decimal(_g(row, 10)),
            'invoiced_value':   _to_decimal(_g(row, 11)),
            'invoice_date':     _to_date_us(_g(row, 12)),
            'invoice_ref':      _to_str(_g(row, 13)),
            'brand':            _to_str(_g(row, 20)),
            'item_number':      _to_str(_g(row, 24)),
            'country':          'United States',
            'currency':         'USD',
        })
    return records


# ---------------------------------------------------------------------------
# Americas: STARIN YTD — read "Invoiced-Shipped" sheet
# Row 1=date-range summary, Row 2=headers, Row 3+=data
# Cols: 0=Invoice#, 1=Order#, 2=Invoice Date, 3=Account#, 4=Account Name,
#       5=Bill To Street, 6=Bill To City, 7=Bill To State, 8=Bill To Zip,
#       9=Ship To Name, 10=Ship To Street, 11=Ship To City, 12=Ship To State,
#       13=Ship To Zip, 14=PO#, 15=Brand, 16=Model, 17=Vendor Model,
#       18=Stock Type, 19=WHS, 20=QTY, 21=Invoice Price, 22=Extended Price,
#       23=Midwich Cost, 24=Extended Cost
# ---------------------------------------------------------------------------

def parse_starin_ytd(wb):
    ws = wb['Invoiced-Shipped']
    records = []
    for row in ws.iter_rows(min_row=3, values_only=True):
        if all(v is None for v in row):
            continue
        d = _to_date_us(_g(row, 2))
        if d is None:
            continue
        records.append({
            'vendor':           'Starin',
            'invoice_ref':      _to_str(_g(row, 0)),
            'order_ref':        _to_str(_g(row, 14)),
            'invoice_date':     d,
            'customer_account': _to_str(_g(row, 3)),
            'customer_name':    _to_str(_g(row, 4)),
            'address_street':   _to_str(_g(row, 5)),
            'address_city':     _to_str(_g(row, 6)),
            'address_county':   _to_str(_g(row, 7)),
            'post_code':        _to_post_code(_g(row, 8)),
            'brand':            _to_str(_g(row, 15)),
            'item_number':      _to_str(_g(row, 16)),
            'manufacturer_part_no': _to_str(_g(row, 17)),
            'quantity':         _to_int(_g(row, 20)),
            'sales_price':      _to_decimal(_g(row, 21)),
            'invoiced_value':   _to_decimal(_g(row, 22)),
            'country':          'United States',
            'currency':         'USD',
        })
    return records


# ---------------------------------------------------------------------------
# Americas: JB&A
# Rows 1-5 = title/header block; Row 6=column headers; Row 7+=data
# Cols: 0=Model#, 1=Item, 2=Date, 3=Qty Sold, 4=Est Extended Cost,
#       5=Sales Price, 6=Ship Country, 7=Ship State, 8=Ship Street,
#       9=Ship City, 10=Ship Zip, 11=Ship Addressee (end-customer),
#       12-15=Billing addr, 16=Customer/Project, 17=Amount(Gross)
# ---------------------------------------------------------------------------

def parse_jba(wb):
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=7, values_only=True):
        if all(v is None for v in row):
            continue
        d = _to_date(_g(row, 2))
        if d is None:
            continue
        records.append({
            'vendor':           'JB&A',
            'manufacturer_part_no': _to_str(_g(row, 0)),
            'item_number':      _to_str(_g(row, 1)),
            'invoice_date':     d,
            'quantity':         _to_int(_g(row, 3)),
            'invoiced_value':   _to_decimal(_g(row, 17)),
            'sales_price':      _to_decimal(_g(row, 5)),
            'country':          _normalize_country_str(_to_str(_g(row, 6))) or 'United States',
            'address_county':   _to_str(_g(row, 7)),
            'address_street':   _to_str(_g(row, 8)),
            'address_city':     _to_str(_g(row, 9)),
            'post_code':        _to_post_code(_g(row, 10)),
            'customer_name':    _to_str(_g(row, 11)),
            'currency':         'USD',
        })
    return records


# ---------------------------------------------------------------------------
# Americas: ACCU-TECH main format (14-column)
# Cols: 0=VENDOR NAME, 1=SELLING BRANCH, 2=BRANCH NAME, 3=CUST REF,
#       4=CUST NAME, 5=BILLING ZIP, 6=SHIP TO CITY, 7=SHIP TO STATE,
#       8=SHIP TO ZIP, 9=VENDOR ITEM (Kramer part#), 10=ATC ITEM,
#       11=EXTND QTY, 12=ENTND AVG COST (total), 13=REPORT END DATE
# ---------------------------------------------------------------------------

def parse_accutech(wb):
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        records.append({
            'vendor':           'Accu-Tech',
            'customer_account': _to_str(_g(row, 3)),
            'customer_name':    _to_str(_g(row, 4)),
            'post_code':        _to_post_code(_g(row, 5)),
            'address_city':     _to_str(_g(row, 6)),
            'address_county':   _to_str(_g(row, 7)),
            'manufacturer_part_no': _to_str(_g(row, 9)),
            'item_number':      _to_str(_g(row, 10)),
            'quantity':         _to_int(_g(row, 11)),
            'invoiced_value':   _to_decimal(_g(row, 12)),
            'invoice_date':     _to_date(_g(row, 13)),
            'country':          'United States',
            'currency':         'USD',
        })
    return records


# ---------------------------------------------------------------------------
# Americas: ACCU-TECH DDP format (17-column)
# Cols: 0=Manufacturer Name, 1=Sales Location, 2=Sales Loc City,
#       3=Bill To Customer#, 4=Bill To Customer Name, 5=Bill To City,
#       6=Bill To State, 7=Bill To Postal, 8=Ship To Customer Name,
#       9=Ship To City, 10=Ship To State, 11=Ship To Postal,
#       12=Mfr Item#, 13=Transactable Part#, 14=Qty, 15=Adj EXT Cost,
#       16=ReportPeriod
# ---------------------------------------------------------------------------

def parse_accutech_ddp(wb):
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        records.append({
            'vendor':           'Accu-Tech',
            'customer_account': _to_str(_g(row, 3)),
            'customer_name':    _to_str(_g(row, 4)),
            'address_city':     _to_str(_g(row, 5)),
            'address_county':   _to_str(_g(row, 6)),
            'post_code':        _to_post_code(_g(row, 7)),
            'manufacturer_part_no': _to_str(_g(row, 12)),
            'quantity':         _to_int(_g(row, 14)),
            'invoiced_value':   _to_decimal(_g(row, 15)),
            'invoice_date':     _to_date_us(_g(row, 16)),
            'country':          'United States',
            'currency':         'USD',
        })
    return records


# ---------------------------------------------------------------------------
# Americas: Anixter (Americas rows only — filter out Theater == 'EMEA')
# No invoice date; derived from Fiscal Year (col 0) + Fiscal Month (col 1)
# Cols: 0=Fiscal Year, 1=Fiscal Month, 9=Item#, 10=Description, 12=Mfr Item#,
#       13=MTD Qty, 14=Unit Cost, 15=MTD Ext Cost, 18=Ship-to Customer#,
#       19=Ship-to Customer Name, 20=Ship-to City, 21=Ship-to State,
#       22=Ship-to Postal, 23=Ship-to Country, 30=Theater
# ---------------------------------------------------------------------------

def parse_anixter_americas(wb):
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        theater = _to_str(_g(row, 30)).upper()
        if theater == 'EMEA':
            continue
        year = _g(row, 0)
        month = _g(row, 1)
        try:
            invoice_date = date(int(year), int(month), 1)
        except (TypeError, ValueError):
            invoice_date = None
        raw_country = _to_str(_g(row, 23)) or _to_str(_g(row, 7))
        records.append({
            'vendor':           'Anixter',
            'invoice_date':     invoice_date,
            'item_number':      _to_str(_g(row, 9)),
            'product_description': _to_str(_g(row, 10)),
            'manufacturer_part_no': _to_str(_g(row, 12)),
            'quantity':         _to_int(_g(row, 13)),
            'sales_price':      _to_decimal(_g(row, 14)),
            'invoiced_value':   _to_decimal(_g(row, 15)),
            'customer_account': _to_str(_g(row, 18)),
            'customer_name':    _to_str(_g(row, 19)),
            'address_city':     _to_str(_g(row, 20)),
            'address_county':   _to_str(_g(row, 21)),
            'post_code':        _to_post_code(_g(row, 22)),
            'country':          _normalize_country_str(raw_country),
            'currency':         'USD',
        })
    return records


# ---------------------------------------------------------------------------
# Americas: monthly distribution summary files
# Extracts only: Graybar, ADI, Tower, TD Synnex
# Skips: Almo, Anixter, Starin, JB&A, AccuTech (handled by individual files)
# ---------------------------------------------------------------------------

def _parse_graybar_sheet(ws):
    # Cols: 0=Invoice Date, 5=Invoice#, 6=Sold To Name, 7=Sold To ID,
    #       8=Sold To Address, 9=City, 10=State, 11=ZIP, 19=Qty,
    #       21=Product Group, 22=Material Catalog, 23=Material Desc, 25=Net Ext Cost
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        d = _to_date(_g(row, 0))
        if d is None:
            continue
        records.append({
            'vendor':           'Graybar',
            'invoice_date':     d,
            'invoice_ref':      _to_str(_g(row, 5)),
            'customer_account': _to_str(_g(row, 7)),
            'customer_name':    _to_str(_g(row, 6)),
            'address_street':   _to_str(_g(row, 8)),
            'address_city':     _to_str(_g(row, 9)),
            'address_county':   _to_str(_g(row, 10)),
            'post_code':        _to_post_code(_g(row, 11)),
            'product_level_1':  _to_str(_g(row, 21)),
            'manufacturer_part_no': _to_str(_g(row, 22)),
            'product_description': _to_str(_g(row, 23)),
            'quantity':         _to_int(_g(row, 19)),
            'invoiced_value':   _to_decimal(_g(row, 25)),
            'country':          'United States',
            'currency':         'USD',
        })
    return records


def _parse_adi_sheet(ws):
    # Cols: 1=Country, 5=Invoice Date, 12=DC City, 13=DC State, 14=DC ZIP,
    #       16=ADI Part#, 17=Vendor Part#, 18=Item Description, 19=RCAT,
    #       21=Units, 22=Cost of Sales
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        d = _to_date(_g(row, 5))
        if d is None:
            continue
        records.append({
            'vendor':           'ADI Global',
            'invoice_date':     d,
            'item_number':      _to_str(_g(row, 16)),
            'manufacturer_part_no': _to_str(_g(row, 17)),
            'product_description': _to_str(_g(row, 18)),
            'product_level_1':  _to_str(_g(row, 19)),
            'quantity':         _to_int(_g(row, 21)),
            'invoiced_value':   _to_decimal(_g(row, 22)),
            'address_city':     _to_str(_g(row, 12)),
            'address_county':   _to_str(_g(row, 13)),
            'post_code':        _to_post_code(_g(row, 14)),
            'country':          _normalize_country_str(_to_str(_g(row, 1))) or 'United States',
            'currency':         'USD',
        })
    return records


def _parse_tower_sheet(ws):
    # Cols: 0=Date, 1=Ship to Company, 2=City, 3=State, 4=ZIP, 5=Bill To,
    #       6=Model (Kramer part#), 7=Qty, 8=Cost, 9=Total
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        d = _to_date(_g(row, 0))
        if d is None:
            continue
        records.append({
            'vendor':           'Tower',
            'invoice_date':     d,
            'customer_name':    _to_str(_g(row, 1)),
            'address_city':     _to_str(_g(row, 2)),
            'address_county':   _to_str(_g(row, 3)),
            'post_code':        _to_post_code(_g(row, 4)),
            'manufacturer_part_no': _to_str(_g(row, 6)),
            'quantity':         _to_int(_g(row, 7)),
            'sales_price':      _to_decimal(_g(row, 8)),
            'invoiced_value':   _to_decimal(_g(row, 9)),
            'country':          'United States',
            'currency':         'USD',
        })
    return records


def _parse_tdsynnex_sheet(ws):
    # Cols: 0=order_no, 3=ship_date, 6=Ship_Qty, 8=Base_Cost, 9=Extend_Base_Cost,
    #       10=bill_to_cust_no, 17=customer_po_no, 20=ship_to_name, 21=ship_to_city,
    #       22=ship_to_zip, 23=ship_to_state, 28=vend_part_no, 29=part_desc
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        d = _to_date(_g(row, 3))
        if d is None:
            continue
        records.append({
            'vendor':           'TD Synnex',
            'invoice_ref':      _to_str(_g(row, 0)),
            'order_ref':        _to_str(_g(row, 17)),
            'invoice_date':     d,
            'customer_account': _to_str(_g(row, 10)),
            'customer_name':    _to_str(_g(row, 20)),
            'address_city':     _to_str(_g(row, 21)),
            'post_code':        _to_post_code(_g(row, 22)),
            'address_county':   _to_str(_g(row, 23)),
            'manufacturer_part_no': _to_str(_g(row, 28)),
            'product_description': _to_str(_g(row, 29)),
            'quantity':         _to_int(_g(row, 6)),
            'sales_price':      _to_decimal(_g(row, 8)),
            'invoiced_value':   _to_decimal(_g(row, 9)),
            'country':          'United States',
            'currency':         'USD',
        })
    return records


_DIST_MONTHLY_HANDLERS = {
    'Graybar':   _parse_graybar_sheet,
    'ADI':       _parse_adi_sheet,
    'Tower':     _parse_tower_sheet,
    'TD Synnex': _parse_tdsynnex_sheet,
    'TD SYNNEX': _parse_tdsynnex_sheet,
}
# Sheets to skip (handled by individual files)
_DIST_MONTHLY_SKIP = {'almo', 'anixter', 'anixter(lizette)', 'starin',
                      'jb&a', 'accutech', 'midwich'}


def parse_americas_distribution(wb):
    """Monthly distribution summary: extract Graybar, ADI, Tower, TD Synnex only."""
    records = []
    for ws in wb.worksheets:
        title = ws.title.strip()
        if title.lower() in _DIST_MONTHLY_SKIP:
            continue
        handler = _DIST_MONTHLY_HANDLERS.get(title)
        if handler:
            records.extend(handler(ws))
    return records


def parse_adi_standalone(wb):
    """ADI-only file (e.g. May standalone)."""
    ws = wb.active
    return _parse_adi_sheet(ws)


# ---------------------------------------------------------------------------
# Registry: maps distributor code → parser function
# ---------------------------------------------------------------------------

PARSERS = {
    'cdev':                  parse_cdev,
    'asean':                 parse_standard_kramer,
    'greater-china':         parse_standard_kramer,
    'northeast-asia':        parse_standard_kramer,
    'oceania':               parse_standard_kramer,
    'saarc':                 parse_standard_kramer,
    'nordic-multi':          parse_nordic_multi_sheet,
    'midwich-zeevee':        parse_midwich_zeevee,
    'emea-kramer':           parse_emea_kramer_format,
    'emea-bomisco':          parse_bomisco_format,
    'almo':                  parse_almo,
    'starin-ytd':            parse_starin_ytd,
    'jba':                   parse_jba,
    'accutech':              parse_accutech,
    'accutech-ddp':          parse_accutech_ddp,
    'anixter-americas':      parse_anixter_americas,
    'americas-distribution': parse_americas_distribution,
    'adi-standalone':        parse_adi_standalone,
}


def get_parser(distributor_code):
    return PARSERS.get(distributor_code.lower())
