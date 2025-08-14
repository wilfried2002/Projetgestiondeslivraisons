from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_today, name='index'),
    path('rapport-livraisons/', views.rapport_livraisons, name='rapport_livraisons'),
    path('rapport-feuilles-route/', views.rapport_feuilles_route, name='rapport_feuilles_route'),
    path('export-csv-livraisons/', views.export_csv_livraisons, name='export_csv_livraisons'),
    path('export-csv-feuilles-route/', views.export_csv_feuilles_route, name='export_csv_feuilles_route'),
]