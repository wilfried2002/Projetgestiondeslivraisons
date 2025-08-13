from django.shortcuts import render
from django.utils import timezone
from livraison.models import FeuilleDeRoute

def dashboard_today(request):
    today = timezone.localdate()
    qs = FeuilleDeRoute.objects.select_related('chauffeur__user').prefetch_related('livraisons')
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
        qs = qs.filter(chauffeur__vehicule__icontains=vehicule)

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


