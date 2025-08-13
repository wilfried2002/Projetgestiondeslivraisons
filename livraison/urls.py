from django.urls import path
from . import views

app_name = 'livraison'

urlpatterns = [
    # path('', views.index, name='index'),
    path('feuille/<uuid:token>/', views.feuille_detail, name='feuille_detail'),
    path('feuille/<uuid:token>/position/', views.update_position, name='update_position'),
    path('livraison/<int:pk>/update/', views.update_livraison_status, name='update_livraison_status'),
    path('track/<uuid:token>/', views.track_livraison, name='track'),
]