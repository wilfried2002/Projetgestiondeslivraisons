from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from livraison.models import FeuilleDeRoute, Livraison, Chauffeur

def chauffeur_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            try:
                chauffeur = Chauffeur.objects.get(user=user)
                login(request, user)
                messages.success(request, f'Bienvenue {chauffeur.user.get_full_name() or chauffeur.user.username}!')
                return redirect('chauffeur:dashboard')
            except Chauffeur.DoesNotExist:
                messages.error(request, 'Vous n\'êtes pas autorisé à accéder à cette interface.')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'chauffeur/login.html')

@login_required
def chauffeur_logout(request):
    logout(request)
    messages.success(request, 'Vous avez été déconnecté.')
    return redirect('chauffeur:login')

@login_required
def chauffeur_dashboard(request):
    try:
        chauffeur = Chauffeur.objects.get(user=request.user)
    except Chauffeur.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas un chauffeur autorisé.')
        return redirect('chauffeur:login')
    
    # Récupérer les feuilles de route du chauffeur avec le véhicule assigné
    feuilles = FeuilleDeRoute.objects.filter(chauffeur=chauffeur).select_related('vehicule').order_by('-date_route', '-date_creation')
    
    # Statistiques
    total_feuilles = feuilles.count()
    feuilles_en_cours = feuilles.filter(statut='en_route').count()
    feuilles_terminees = feuilles.filter(statut='terminee').count()
    
    # Trouver le véhicule actuellement assigné (feuille en cours ou planifiée)
    vehicule_actuel = None
    for feuille in feuilles:
        if feuille.vehicule and feuille.statut in ['planifie', 'en_route']:
            vehicule_actuel = feuille.vehicule
            break
    
    context = {
        'chauffeur': chauffeur,
        'feuilles': feuilles,
        'vehicule_actuel': vehicule_actuel,
        'total_feuilles': total_feuilles,
        'feuilles_en_cours': feuilles_en_cours,
        'feuilles_terminees': feuilles_terminees,
    }
    return render(request, 'chauffeur/dashboard.html', context)

@login_required
def feuille_detail_chauffeur(request, feuille_id):
    try:
        chauffeur = Chauffeur.objects.get(user=request.user)
        feuille = get_object_or_404(FeuilleDeRoute, id=feuille_id, chauffeur=chauffeur)
    except Chauffeur.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas un chauffeur autorisé.')
        return redirect('chauffeur:login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'start_route':
            feuille.statut = 'en_route'
            feuille.save()
            messages.success(request, 'Feuille de route marquée comme "En route"')
        elif action == 'finish_route':
            feuille.statut = 'terminee'
            feuille.save()
            messages.success(request, 'Feuille de route marquée comme "Terminée"')
        elif action == 'problem_route':
            feuille.statut = 'probleme'
            feuille.save()
            messages.warning(request, 'Feuille de route marquée comme "Problème"')
        elif action == 'update_observations':
            observations = request.POST.get('observations_chauffeur', '').strip()
            if observations:
                feuille.observations_chauffeur = observations
                feuille.date_observations = timezone.now()
                feuille.save(update_fields=['observations_chauffeur', 'date_observations'])
                messages.success(request, 'Observations mises à jour')
        
        return redirect('chauffeur:feuille_detail', feuille_id=feuille_id)
    
    livraisons = feuille.livraisons.select_related('client').prefetch_related('produits', 'sacs').all()
    
    context = {
        'feuille': feuille,
        'livraisons': livraisons,
        'chauffeur': chauffeur,
    }
    return render(request, 'chauffeur/feuille_detail.html', context)