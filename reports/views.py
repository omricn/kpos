import csv
import openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Min, Max, Q
from django.http import HttpResponse
from django.utils import timezone

from .models import Distributor, POSUpload, POSRecord
from .forms import UploadForm
from .parsers import get_parser


def dashboard(request):
    distributors = Distributor.objects.all()
    dist_data = []
    for d in distributors:
        latest = d.uploads.order_by('-uploaded_at').first()
        stats = d.records.aggregate(
            total_records=Count('id'),
            total_qty=Sum('quantity'),
            total_value=Sum('invoiced_value'),
            date_from=Min('invoice_date'),
            date_to=Max('invoice_date'),
        )
        dist_data.append({
            'distributor': d,
            'latest_upload': latest,
            'stats': stats,
        })

    context = {
        'dist_data': dist_data,
        'page_title': 'Dashboard',
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
                ws = wb.active
                parsed_rows = parser(ws)
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


def distributor_list(request):
    distributors = Distributor.objects.all()
    return render(request, 'reports/distributor_list.html', {
        'distributors': distributors,
        'page_title': 'Distributors',
    })
