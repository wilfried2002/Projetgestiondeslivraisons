from django.urls import path
from . import views  # Adjust according to your views

app_name = 'chauffeur'  # Ensure this line is present

urlpatterns = [
    path('login/', views.chauffeur_login, name='login'),
    path('logout/', views.chauffeur_logout, name='logout'),
    path('', views.chauffeur_dashboard, name='dashboard'),
    path('feuille/<int:feuille_id>/', views.feuille_detail_chauffeur, name='feuille_detail'),
]