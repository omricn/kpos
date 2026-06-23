from django.contrib import admin
from .models import Distributor, POSUpload, POSRecord, PrioritySalesperson, PriorityProduct, CustomerSalesRep


@admin.register(Distributor)
class DistributorAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'country', 'region', 'priority_customer_code', 'salesperson_name', 'created_at']
    prepopulated_fields = {'code': ('name',)}
    fieldsets = [
        (None, {'fields': ['name', 'code', 'country', 'region', 'notes']}),
        ('Priority ERP', {'fields': ['priority_customer_code', 'salesperson_code', 'salesperson_name'],
                          'description': 'Set priority_customer_code to the Priority CUSTNAME for this distributor, then run: python manage.py sync_priority --agents-only'}),
    ]


@admin.register(PrioritySalesperson)
class PrioritySalespersonAdmin(admin.ModelAdmin):
    list_display = ['agent_code', 'agent_name', 'synced_at']
    search_fields = ['agent_code', 'agent_name']
    readonly_fields = ['synced_at']


@admin.register(PriorityProduct)
class PriorityProductAdmin(admin.ModelAdmin):
    list_display = ['part_number', 'description', 'family', 'status', 'synced_at']
    search_fields = ['part_number', 'description']
    list_filter = ['status', 'family']
    readonly_fields = ['synced_at']


@admin.register(CustomerSalesRep)
class CustomerSalesRepAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'salesperson', 'effective_from', 'created_at']
    search_fields = ['customer_name', 'salesperson__agent_name']
    list_filter = ['salesperson']
    ordering = ['customer_name', '-effective_from']


@admin.register(POSUpload)
class POSUploadAdmin(admin.ModelAdmin):
    list_display = ['distributor', 'original_filename', 'report_period', 'row_count', 'uploaded_at']
    list_filter = ['distributor']


@admin.register(POSRecord)
class POSRecordAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'product_name', 'quantity', 'invoiced_value', 'currency', 'invoice_date', 'distributor']
    list_filter = ['distributor', 'currency', 'product_level_1']
    search_fields = ['customer_name', 'product_name', 'item_number', 'order_ref']
