from django.db import models


class Distributor(models.Model):
    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=50, unique=True)
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Priority ERP link (set manually in admin, synced by sync_priority command)
    priority_customer_code = models.CharField(
        max_length=50, blank=True,
        help_text='Priority CUSTNAME code for this distributor (e.g. CDEV)',
    )
    salesperson_code = models.CharField(max_length=50, blank=True)
    salesperson_name = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def latest_upload(self):
        return self.uploads.order_by('-uploaded_at').first()

    def record_count(self):
        return self.records.count()


class POSUpload(models.Model):
    distributor = models.ForeignKey(Distributor, on_delete=models.CASCADE, related_name='uploads')
    original_filename = models.CharField(max_length=255)
    report_period = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    row_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.distributor.name} — {self.uploaded_at.strftime('%Y-%m-%d')} ({self.row_count} rows)"


class POSRecord(models.Model):
    upload = models.ForeignKey(POSUpload, on_delete=models.CASCADE, related_name='records')
    distributor = models.ForeignKey(Distributor, on_delete=models.CASCADE, related_name='records')

    # Product hierarchy
    product_level_1 = models.CharField(max_length=200, blank=True)
    product_level_2 = models.CharField(max_length=200, blank=True)
    product_level_3 = models.CharField(max_length=200, blank=True)
    item_number = models.CharField(max_length=100, blank=True, db_index=True)
    brand = models.CharField(max_length=100, blank=True)
    product_name = models.CharField(max_length=200, blank=True)
    manufacturer_part_no = models.CharField(max_length=100, blank=True)
    product_description = models.TextField(blank=True)
    sales_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Order
    order_ref = models.CharField(max_length=100, blank=True)
    vendor = models.CharField(max_length=200, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    invoiced_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, blank=True, db_index=True)
    invoice_date = models.DateField(null=True, blank=True, db_index=True)
    invoice_ref = models.CharField(max_length=100, blank=True)
    sda_number = models.CharField(max_length=100, blank=True)
    special_bid_number = models.CharField(max_length=100, blank=True)

    # Customer
    customer_account = models.CharField(max_length=100, blank=True)
    customer_name = models.CharField(max_length=200, blank=True, db_index=True)
    address_street = models.CharField(max_length=300, blank=True)
    address_city = models.CharField(max_length=100, blank=True)
    address_county = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    post_code = models.CharField(max_length=20, blank=True)
    telephone = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-invoice_date', 'customer_name']

    def __str__(self):
        return f"{self.customer_name} — {self.product_name} ({self.invoice_date})"


class ExchangeRate(models.Model):
    currency = models.CharField(max_length=3, unique=True)
    rate_to_usd = models.DecimalField(max_digits=12, decimal_places=6)
    rate_to_eur = models.DecimalField(max_digits=12, decimal_places=6)
    fetched_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency}: 1 = ${self.rate_to_usd} / €{self.rate_to_eur}"


class MonthlyRate(models.Model):
    """Historical monthly exchange rates from ECB (rates as of month average)."""
    year = models.IntegerField()
    month = models.IntegerField()
    currency = models.CharField(max_length=3)
    rate_to_usd = models.DecimalField(max_digits=12, decimal_places=6)
    rate_to_eur = models.DecimalField(max_digits=12, decimal_places=6)

    class Meta:
        unique_together = [('year', 'month', 'currency')]
        indexes = [models.Index(fields=['year', 'month', 'currency'])]

    def __str__(self):
        return f"{self.currency} {self.year}-{self.month:02d}: 1 = ${self.rate_to_usd} / €{self.rate_to_eur}"


class PrioritySalesperson(models.Model):
    """Cached copy of Priority AGENTS — Kramer sales reps."""
    agent_code = models.CharField(max_length=50, unique=True)
    agent_name = models.CharField(max_length=200, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['agent_name']

    def __str__(self):
        return f"{self.agent_code} — {self.agent_name}"


class PriorityProduct(models.Model):
    """Cached copy of Priority LOGPART — Kramer product catalog."""
    part_number = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=500, blank=True)    # EPARTDES (English)
    description_local = models.CharField(max_length=500, blank=True)  # PARTDES
    family = models.CharField(max_length=100, blank=True)         # FAMILYNAME
    family_description = models.CharField(max_length=200, blank=True)  # FAMILYDES
    status = models.CharField(max_length=50, blank=True)          # STATDES (Active/Inactive)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['part_number']

    def __str__(self):
        return f"{self.part_number} — {self.description or self.description_local}"
