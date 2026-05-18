import csv
import json
import openpyxl
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Min, Max, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone

from .models import Distributor, POSUpload, POSRecord
from .forms import UploadForm
from .parsers import get_parser

DIST_COLORS = [
    '#8205B4', '#0EA5E9', '#F59E0B', '#10B981', '#EF4444', '#6366F1',
    '#EC4899', '#14B8A6', '#F97316', '#84CC16',
]


def dashboard(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    region = request.GET.get('region', '')
    distributor_id = request.GET.get('distributor', '')

    qs = POSRecord.objects.select_related('distributor')
    if date_from:
        qs = qs.filter(invoice_date__gte=date_from)
    if date_to:
        qs = qs.filter(invoice_date__lte=date_to)
    if region:
        qs = qs.filter(distributor__region=region)
    if distributor_id:
        qs = qs.filter(distributor_id=distributor_id)

    totals = qs.aggregate(
        total_revenue=Sum('invoiced_value'),
        total_units=Sum('quantity'),
        unique_countries=Count('country', distinct=True),
    )
    active_distributors = qs.values('distributor').distinct().count()

    # Monthly revenue per distributor for chart
    monthly_qs = list(
        qs.filter(invoice_date__isnull=False, invoiced_value__isnull=False)
        .annotate(month=TruncMonth('invoice_date'))
        .values('month', 'distributor__id', 'distributor__name', 'distributor__code')
        .annotate(revenue=Sum('invoiced_value'))
        .order_by('month', 'distributor__name')
    )

    months_sorted = sorted(set(r['month'] for r in monthly_qs))
    month_labels = [m.strftime('%b %Y') for m in months_sorted]
    month_keys = [m.strftime('%Y-%m') for m in months_sorted]

    # Build per-distributor dataset
    dist_order = {}
    for r in monthly_qs:
        did = r['distributor__id']
        if did not in dist_order:
            dist_order[did] = {
                'name': r['distributor__name'],
                'by_month': {},
            }
        mk = r['month'].strftime('%Y-%m')
        dist_order[did]['by_month'][mk] = float(r['revenue'])

    datasets = []
    for idx, (did, info) in enumerate(dist_order.items()):
        color = DIST_COLORS[idx % len(DIST_COLORS)]
        datasets.append({
            'label': info['name'],
            'data': [info['by_month'].get(mk, 0) for mk in month_keys],
            'backgroundColor': color,
            'borderColor': color,
            'borderWidth': 0,
            'borderRadius': 4,
            'distId': did,
        })

    chart_data = json.dumps({'labels': month_labels, 'datasets': datasets})

    # Per-distributor summary table
    dist_summary = list(
        qs.values('distributor__id', 'distributor__name', 'distributor__region', 'distributor__code')
        .annotate(
            revenue=Sum('invoiced_value'),
            units=Sum('quantity'),
            countries=Count('country', distinct=True),
            records=Count('id'),
        )
        .order_by('-revenue')
    )

    all_regions = Distributor.objects.exclude(region='').values_list('region', flat=True).distinct().order_by('region')
    all_distributors = Distributor.objects.all().order_by('name')

    context = {
        'total_revenue': float(totals['total_revenue'] or 0),
        'total_units': totals['total_units'] or 0,
        'active_distributors': active_distributors,
        'unique_countries': totals['unique_countries'] or 0,
        'chart_data': chart_data,
        'dist_summary': dist_summary,
        'all_regions': all_regions,
        'all_distributors': all_distributors,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'region': region,
            'distributor': distributor_id,
        },
        'page_title': 'Revenue Dashboard',
        'has_filters': any([date_from, date_to, region, distributor_id]),
    }
    return render(request, 'reports/dashboard.html', context)


def distributor_records(request, pk):
    distributor = get_object_or_404(Distributor, pk=pk)
    records = POSRecord.objects.filter(distributor=distributor).select_related('upload')

    # Filters
    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    category = request.GET.get('category', '').strip()
    upload_id = request.GET.get('upload', '').strip()

    if q:
        records = records.filter(
            Q(customer_name__icontains=q) |
            Q(product_name__icontains=q) |
            Q(item_number__icontains=q) |
            Q(order_ref__icontains=q) |
            Q(address_city__icontains=q)
        )
    if date_from:
        records = records.filter(invoice_date__gte=date_from)
    if date_to:
        records = records.filter(invoice_date__lte=date_to)
    if category:
        records = records.filter(product_level_1=category)
    if upload_id:
        records = records.filter(upload_id=upload_id)

    # Summary stats for filtered results
    stats = records.aggregate(
        total_records=Count('id'),
        total_qty=Sum('quantity'),
        total_value=Sum('invoiced_value'),
        unique_customers=Count('customer_name', distinct=True),
        date_from=Min('invoice_date'),
        date_to=Max('invoice_date'),
    )

    # Filter options
    categories = POSRecord.objects.filter(distributor=distributor).values_list(
        'product_level_1', flat=True).distinct().exclude(product_level_1='').order_by('product_level_1')
    uploads = distributor.uploads.all()

    context = {
        'distributor': distributor,
        'records': records,
        'stats': stats,
        'categories': categories,
        'uploads': uploads,
        'filters': {
            'q': q,
            'date_from': date_from,
            'date_to': date_to,
            'category': category,
            'upload': upload_id,
        },
        'page_title': distributor.name,
    }
    return render(request, 'reports/records.html', context)


def upload_file(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            distributor = form.cleaned_data['distributor']
            excel_file = request.FILES['excel_file']
            report_period = form.cleaned_data['report_period']
            replace_existing = form.cleaned_data['replace_existing']
            notes = form.cleaned_data['notes']

            parser = get_parser(distributor.code)
            if not parser:
                messages.error(request, f'No parser configured for distributor "{distributor.name}" (code: {distributor.code}). Contact the system administrator.')
                return render(request, 'reports/upload.html', {'form': form, 'page_title': 'Upload Report'})

            try:
                wb = openpyxl.load_workbook(excel_file, data_only=True)
                parsed_rows = parser(wb)
            except Exception as e:
                messages.error(request, f'Failed to parse Excel file: {e}')
                return render(request, 'reports/upload.html', {'form': form, 'page_title': 'Upload Report'})

            if not parsed_rows:
                messages.error(request, 'No data rows found in the uploaded file.')
                return render(request, 'reports/upload.html', {'form': form, 'page_title': 'Upload Report'})

            if replace_existing:
                POSRecord.objects.filter(distributor=distributor).delete()
                distributor.uploads.all().delete()

            upload = POSUpload.objects.create(
                distributor=distributor,
                original_filename=excel_file.name,
                report_period=report_period,
                row_count=len(parsed_rows),
                notes=notes,
            )

            bulk_records = [
                POSRecord(upload=upload, distributor=distributor, **row)
                for row in parsed_rows
            ]
            POSRecord.objects.bulk_create(bulk_records)

            messages.success(request, f'Successfully imported {len(parsed_rows)} records from "{excel_file.name}".')
            return redirect('distributor_records', pk=distributor.pk)
    else:
        form = UploadForm()

    return render(request, 'reports/upload.html', {'form': form, 'page_title': 'Upload Report'})


def export_csv(request, pk):
    distributor = get_object_or_404(Distributor, pk=pk)
    records = POSRecord.objects.filter(distributor=distributor).order_by('-invoice_date')

    # Apply same filters as records view
    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    category = request.GET.get('category', '').strip()

    if q:
        records = records.filter(
            Q(customer_name__icontains=q) |
            Q(product_name__icontains=q) |
            Q(item_number__icontains=q) |
            Q(order_ref__icontains=q)
        )
    if date_from:
        records = records.filter(invoice_date__gte=date_from)
    if date_to:
        records = records.filter(invoice_date__lte=date_to)
    if category:
        records = records.filter(product_level_1=category)

    filename = f"POS_{distributor.code}_{timezone.now().strftime('%Y%m%d')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice Date', 'Invoice Ref', 'Order Ref',
        'Customer Account', 'Customer Name', 'City', 'Country',
        'Item Number', 'Product Name', 'Manufacturer Part No', 'Description',
        'Category L1', 'Category L2', 'Category L3',
        'Brand', 'Quantity', 'Sales Price', 'Invoiced Value', 'Currency',
        'Vendor', 'SDA Number', 'Special Bid',
        'Address', 'Post Code', 'Telephone',
    ])
    for r in records:
        writer.writerow([
            r.invoice_date, r.invoice_ref, r.order_ref,
            r.customer_account, r.customer_name, r.address_city, r.country,
            r.item_number, r.product_name, r.manufacturer_part_no, r.product_description,
            r.product_level_1, r.product_level_2, r.product_level_3,
            r.brand, r.quantity, r.sales_price, r.invoiced_value, r.currency,
            r.vendor, r.sda_number, r.special_bid_number,
            r.address_street, r.post_code, r.telephone,
        ])

    return response


REGION_COLORS = {
    'ASEAN':          '#10B981',
    'Greater China':  '#0EA5E9',
    'Northeast Asia': '#F59E0B',
    'Oceania':        '#EF4444',
    'SAARC':          '#6366F1',
    'Europe':         '#8205B4',
}


def distributor_list(request):
    selected_region = request.GET.get('region', '').strip()

    all_distributors = Distributor.objects.all().order_by('name')

    region_qs = (
        POSRecord.objects
        .values('distributor__region')
        .annotate(
            revenue=Sum('invoiced_value'),
            records=Count('id'),
            dist_count=Count('distributor', distinct=True),
        )
        .order_by('distributor__region')
    )
    region_stats = [
        {
            'name': r['distributor__region'] or 'Unknown',
            'revenue': float(r['revenue'] or 0),
            'records': r['records'] or 0,
            'dist_count': r['dist_count'] or 0,
            'color': REGION_COLORS.get(r['distributor__region'], '#6c757d'),
        }
        for r in region_qs
    ]

    filtered_distributors = None
    if selected_region:
        filtered_distributors = list(
            Distributor.objects
            .filter(region=selected_region)
            .annotate(
                total_records=Count('records'),
                total_revenue=Sum('records__invoiced_value'),
            )
            .order_by('-total_revenue')
        )

    return render(request, 'reports/distributor_list.html', {
        'all_distributors': all_distributors,
        'region_stats': region_stats,
        'selected_region': selected_region,
        'filtered_distributors': filtered_distributors,
        'page_title': 'Distributors',
    })
