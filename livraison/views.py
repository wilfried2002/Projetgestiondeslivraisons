from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # keep CSRF for forms; can exempt GPS endpoint if needed
from .models import FeuilleDeRoute, Livraison
import json

# def index(request):
#     return HttpResponse("Welcome to the Livraison app!")

def feuille_detail(request, token):
    feuille = get_object_or_404(FeuilleDeRoute, token=token)
    livraisons = feuille.livraisons.select_related('client').all().order_by('horaire_estime', 'id')
    
    if request.method == 'POST':
        if 'start_route' in request.POST:
            feuille.statut = 'en_route'
            feuille.save(update_fields=['statut'])
            return redirect('livraison:feuille_detail', token=token)
        elif 'update_observations' in request.POST:
            observations = request.POST.get('observations_chauffeur', '').strip()
            if observations:
                feuille.observations_chauffeur = observations
                feuille.date_observations = timezone.now()
                feuille.save(update_fields=['observations_chauffeur', 'date_observations'])
            return redirect('livraison:feuille_detail', token=token)
    
    context = {'feuille': feuille, 'livraisons': livraisons}
    return render(request, 'livraison/feuille_detail.html', context)

@require_POST
def update_livraison_status(request, pk):
    livraison = get_object_or_404(Livraison, pk=pk)
    statut = request.POST.get('statut')
    if statut in dict(livraison._meta.get_field('statut').choices):
        livraison.statut = statut
        if statut == 'livre' and not livraison.date_livraison:
            livraison.date_livraison = timezone.now()
    
    if 'preuve_photo' in request.FILES:
        livraison.preuve_photo = request.FILES['preuve_photo']
    if 'signature_client' in request.FILES:
        livraison.signature_client = request.FILES['signature_client']
    if 'signature_tactile' in request.POST:
        signature_tactile = request.POST.get('signature_tactile', '').strip()
        if signature_tactile:
            livraison.signature_tactile = signature_tactile
    
    livraison.save()
    return redirect('livraison:feuille_detail', token=livraison.feuille.token)

@require_POST
def update_position(request, token):
    feuille = get_object_or_404(FeuilleDeRoute, token=token)
    lat = request.POST.get('lat') or request.GET.get('lat')
    lng = request.POST.get('lng') or request.GET.get('lng')
    if not lat or not lng:
        return JsonResponse({'ok': False, 'error': 'lat/lng required'}, status=400)
    try:
        feuille.last_latitude = float(lat)
        feuille.last_longitude = float(lng)
        feuille.last_position_at = timezone.now()
        feuille.save(update_fields=['last_latitude', 'last_longitude', 'last_position_at'])
        return JsonResponse({'ok': True})
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'invalid lat/lng'}, status=400)

def track_livraison(request, token):
    livraison = get_object_or_404(Livraison, public_token=token)
    return render(request, 'livraison/track.html', {'livraison': livraison})
