from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_file, name='upload'),
    path('distributors/', views.distributor_list, name='distributor_list'),
    path('distributor/<int:pk>/', views.distributor_records, name='distributor_records'),
    path('distributor/<int:pk>/export/', views.export_csv, name='export_csv'),
    path('countries/', views.countries_view, name='countries'),
    path('units/', views.units_view, name='units'),
    path('revenue/', views.revenue_view, name='revenue'),
    path('weekly/', views.weekly_view, name='weekly'),
    path('products/', views.product_list, name='product_list'),
    path('products/detail/', views.product_detail, name='product_detail'),
    path('set-currency/', views.set_currency, name='set_currency'),
    path('set-region/', views.set_region, name='set_region'),
    path('salespersons/', views.salesperson_list, name='salesperson_list'),
    path('ai-chat/', views.ai_chat, name='ai_chat'),
    path('ai-export/', views.ai_export, name='ai_export'),
    path('ai-clear/', views.ai_clear, name='ai_clear'),
    path('ai-history/', views.ai_history, name='ai_history'),
]
