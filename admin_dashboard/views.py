from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Count, Sum, Q
from django.contrib.admin.views.decorators import staff_member_required
from livraison.models import FeuilleDeRoute, Livraison, Produit, Chauffeur, Vehicule
from datetime import datetime, timedelta
import csv

def dashboard_today(request):
    today = timezone.localdate()
    qs = FeuilleDeRoute.objects.select_related('chauffeur__user', 'vehicule').prefetch_related('livraisons')
    date_filter = request.GET.get('date') or today.isoformat()
    qs = qs.filter(date_route=date_filter) if request.GET.get('date') else qs.filter(date_route=today)

    chauffeur_id = request.GET.get('chauffeur')
    statut = request.GET.get('statut')
    vehicule = request.GET.get('vehicule')

    if chauffeur_id:
        qs = qs.filter(chauffeur_id=chauffeur_id)
    if statut:
        qs = qs.filter(statut=statut)
    if vehicule:
        qs = qs.filter(vehicule__immatriculation__icontains=vehicule)

    def feuille_status_summary(f):
        total = f.livraisons.count()
        livre = f.livraisons.filter(statut='livre').count()
        probleme = f.livraisons.filter(statut='probleme').count()
        en_cours = total - livre - probleme
        if probleme > 0:
            color = 'red'
        elif livre == total and total > 0:
            color = 'green'
        else:
            color = 'orange'
        return {'total': total, 'livre': livre, 'probleme': probleme, 'en_cours': en_cours, 'color': color}

    feuilles = [(f, feuille_status_summary(f)) for f in qs.order_by('chauffeur__user__last_name', 'id')]
    return render(request, 'admin_dashboard/dashboard.html', {'feuilles': feuilles, 'date_filter': date_filter})

@staff_member_required
def rapport_livraisons(request):
    """Rapport analytique des livraisons"""
    date_debut = request.GET.get('date_debut', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_fin = request.GET.get('date_fin', timezone.now().strftime('%Y-%m-%d'))
    chauffeur_id = request.GET.get('chauffeur')
    statut = request.GET.get('statut')
    
    # Filtres de base
    livraisons = Livraison.objects.select_related(
        'feuille__chauffeur__user', 
        'feuille__vehicule', 
        'client'
    ).prefetch_related('produits', 'sacs')
    
    if date_debut:
        livraisons = livraisons.filter(feuille__date_route__gte=date_debut)
    if date_fin:
        livraisons = livraisons.filter(feuille__date_route__lte=date_fin)
    if chauffeur_id:
        livraisons = livraisons.filter(feuille__chauffeur_id=chauffeur_id)
    if statut:
        livraisons = livraisons.filter(statut=statut)
    
    # Statistiques globales
    total_livraisons = livraisons.count()
    livraisons_livrees = livraisons.filter(statut='livre').count()
    livraisons_probleme = livraisons.filter(statut='probleme').count()
    taux_livraison = (livraisons_livrees / total_livraisons * 100) if total_livraisons > 0 else 0
    
    # Statistiques par chauffeur
    stats_chauffeur = livraisons.values(
        'feuille__chauffeur__user__first_name',
        'feuille__chauffeur__user__last_name'
    ).annotate(
        total=Count('id'),
        livre=Count('id', filter=Q(statut='livre')),
        probleme=Count('id', filter=Q(statut='probleme'))
    ).order_by('-total')
    
    # Statistiques par véhicule
    stats_vehicule = livraisons.values(
        'feuille__vehicule__marque',
        'feuille__vehicule__modele',
        'feuille__vehicule__immatriculation'
    ).annotate(
        total=Count('id'),
        livre=Count('id', filter=Q(statut='livre')),
        probleme=Count('id', filter=Q(statut='probleme'))
    ).order_by('-total')
    
    # Analyse financière par produit
    analyse_produits = {}
    for livraison in livraisons.filter(statut='livre'):
        for produit in livraison.produits.all():
            if produit.nom not in analyse_produits:
                analyse_produits[produit.nom] = {
                    'quantite': 0,
                    'montant': 0,
                    'prix_unitaire': produit.prix_unitaire
                }
            analyse_produits[produit.nom]['quantite'] += livraison.quantite
            analyse_produits[produit.nom]['montant'] += produit.prix_unitaire * livraison.quantite
    
    # Tri par montant décroissant
    analyse_produits = dict(sorted(analyse_produits.items(), key=lambda x: x[1]['montant'], reverse=True))
    
    context = {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_livraisons': total_livraisons,
        'livraisons_livrees': livraisons_livrees,
        'livraisons_probleme': livraisons_probleme,
        'taux_livraison': taux_livraison,
        'stats_chauffeur': stats_chauffeur,
        'stats_vehicule': stats_vehicule,
        'analyse_produits': analyse_produits,
        'livraisons': livraisons.order_by('-feuille__date_route', '-id')[:100],  # Limiter à 100 pour l'affichage
        'chauffeurs': Chauffeur.objects.all(),
    }
    
    return render(request, 'admin_dashboard/rapport_livraisons.html', context)

@staff_member_required
def rapport_feuilles_route(request):
    """Rapport des feuilles de route par statut"""
    date_debut = request.GET.get('date_debut', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_fin = request.GET.get('date_fin', timezone.now().strftime('%Y-%m-%d'))
    statut = request.GET.get('statut')
    
    feuilles = FeuilleDeRoute.objects.select_related(
        'chauffeur__user', 
        'vehicule'
    ).prefetch_related('livraisons')
    
    if date_debut:
        feuilles = feuilles.filter(date_route__gte=date_debut)
    if date_fin:
        feuilles = feuilles.filter(date_route__lte=date_fin)
    if statut:
        feuilles = feuilles.filter(statut=statut)
    
    # Statistiques par statut
    stats_statut = feuilles.values('statut').annotate(
        total=Count('id'),
        total_livraisons=Count('livraisons'),
        livraisons_livrees=Count('livraisons', filter=Q(livraisons__statut='livre')),
        livraisons_probleme=Count('livraisons', filter=Q(livraisons__statut='probleme'))
    ).order_by('statut')
    
    # Statistiques par chauffeur
    stats_chauffeur = feuilles.values(
        'chauffeur__user__first_name',
        'chauffeur__user__last_name'
    ).annotate(
        total=Count('id'),
        planifie=Count('id', filter=Q(statut='planifie')),
        en_route=Count('id', filter=Q(statut='en_route')),
        terminee=Count('id', filter=Q(statut='terminee')),
        probleme=Count('id', filter=Q(statut='probleme'))
    ).order_by('-total')
    
    context = {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'stats_statut': stats_statut,
        'stats_chauffeur': stats_chauffeur,
        'feuilles': feuilles.order_by('-date_route', '-id'),
        'total_feuilles': feuilles.count(),
    }
    
    return render(request, 'admin_dashboard/rapport_feuilles_route.html', context)

@staff_member_required
def export_csv_livraisons(request):
    """Export CSV des livraisons"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="livraisons_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Date Route', 'Chauffeur', 'Véhicule', 'Client', 'Référence', 
        'Quantité', 'Statut', 'Date Livraison', 'Produits', 'Montant Total'
    ])
    
    livraisons = Livraison.objects.select_related(
        'feuille__chauffeur__user', 
        'feuille__vehicule', 
        'client'
    ).prefetch_related('produits').order_by('-feuille__date_route', '-id')
    
    for livraison in livraisons:
        produits_str = ', '.join([f"{p.nom} ({p.prix_unitaire} FCFA)" for p in livraison.produits.all()])
        montant_total = sum(p.prix_unitaire * livraison.quantite for p in livraison.produits.all())
        
        writer.writerow([
            livraison.id,
            livraison.feuille.date_route or livraison.feuille.date_creation,
            livraison.feuille.chauffeur.user.get_full_name() or livraison.feuille.chauffeur.user.username,
            f"{livraison.feuille.vehicule.marque} {livraison.feuille.vehicule.modele}" if livraison.feuille.vehicule else "Non assigné",
            livraison.client.nom,
            livraison.reference_commande,
            livraison.quantite,
            livraison.get_statut_display(),
            livraison.date_livraison.strftime('%Y-%m-%d %H:%M') if livraison.date_livraison else '',
            produits_str,
            f"{montant_total} FCFA"
        ])
    
    return response

@staff_member_required
def export_csv_feuilles_route(request):
    """Export CSV des feuilles de route"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="feuilles_route_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Date Route', 'Chauffeur', 'Véhicule', 'Statut', 
        'Total Livraisons', 'Livraisons Livrées', 'Livraisons Problème',
        'Observations Chauffeur', 'Date Observations'
    ])
    
    feuilles = FeuilleDeRoute.objects.select_related(
        'chauffeur__user', 
        'vehicule'
    ).prefetch_related('livraisons').order_by('-date_route', '-id')
    
    for feuille in feuilles:
        total_livraisons = feuille.livraisons.count()
        livraisons_livrees = feuille.livraisons.filter(statut='livre').count()
        livraisons_probleme = feuille.livraisons.filter(statut='probleme').count()
        
        writer.writerow([
            feuille.id,
            feuille.date_route or feuille.date_creation,
            feuille.chauffeur.user.get_full_name() or feuille.chauffeur.user.username,
            f"{feuille.vehicule.marque} {feuille.vehicule.modele}" if feuille.vehicule else "Non assigné",
            feuille.get_statut_display(),
            total_livraisons,
            livraisons_livrees,
            livraisons_probleme,
            feuille.observations_chauffeur or '',
            feuille.date_observations.strftime('%Y-%m-%d %H:%M') if feuille.date_observations else ''
        ])
    
    return response


