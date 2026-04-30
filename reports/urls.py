from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_file, name='upload'),
    path('distributors/', views.distributor_list, name='distributor_list'),
    path('distributor/<int:pk>/', views.distributor_records, name='distributor_records'),
    path('distributor/<int:pk>/export/', views.export_csv, name='export_csv'),
]
