from django.contrib import admin
from .models import Distributor, POSUpload, POSRecord


@admin.register(Distributor)
class DistributorAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'country', 'created_at']
    prepopulated_fields = {'code': ('name',)}


@admin.register(POSUpload)
class POSUploadAdmin(admin.ModelAdmin):
    list_display = ['distributor', 'original_filename', 'report_period', 'row_count', 'uploaded_at']
    list_filter = ['distributor']


@admin.register(POSRecord)
class POSRecordAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'product_name', 'quantity', 'invoiced_value', 'currency', 'invoice_date', 'distributor']
    list_filter = ['distributor', 'currency', 'product_level_1']
    search_fields = ['customer_name', 'product_name', 'item_number', 'order_ref']
