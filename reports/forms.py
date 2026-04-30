from django import forms
from .models import Distributor


class UploadForm(forms.Form):
    distributor = forms.ModelChoiceField(
        queryset=Distributor.objects.all(),
        empty_label='— Select distributor —',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    report_period = forms.CharField(
        max_length=100,
        required=False,
        help_text='e.g. "April 2026" or "Week 17"',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. April 2026'}),
    )
    excel_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'}),
    )
    replace_existing = forms.BooleanField(
        required=False,
        initial=False,
        label='Replace all existing records for this distributor',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    notes = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes about this upload'}),
    )
