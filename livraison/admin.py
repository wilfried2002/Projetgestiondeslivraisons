from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Chauffeur, Client, FeuilleDeRoute, Livraison, Produit, Sac

# Personnalisation du site admin
admin.site.site_header = "🚚 Administration - Suivi de Livraison"
admin.site.site_title = "Suivi de Livraison"
admin.site.index_title = "Tableau de bord - Gestion des livraisons"


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prix_unitaire', 'actif', 'date_creation')
    list_filter = ('actif', 'date_creation')
    search_fields = ('nom', 'description')
    list_editable = ('actif', 'prix_unitaire')
    ordering = ('nom',)
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'description', 'prix_unitaire')
        }),
        ('Statut', {
            'fields': ('actif',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Sac)
class SacAdmin(admin.ModelAdmin):
    list_display = ('nom', 'couleur', 'capacite', 'actif', 'date_creation')
    list_filter = ('actif', 'couleur', 'date_creation')
    search_fields = ('nom', 'description', 'couleur')
    list_editable = ('actif', 'couleur')
    ordering = ('nom',)
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'description', 'couleur', 'capacite')
        }),
        ('Statut', {
            'fields': ('actif',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Chauffeur)
class ChauffeurAdmin(admin.ModelAdmin):
    list_display = ('user', 'telephone', 'vehicule', 'immatriculation', 'get_full_name')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'immatriculation', 'vehicule')
    list_filter = ('vehicule',)
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = "Nom complet"
    
    fieldsets = (
        ('Informations utilisateur', {
            'fields': ('user',)
        }),
        ('Informations professionnelles', {
            'fields': ('telephone', 'vehicule', 'immatriculation')
        }),
    )


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'adresse_courte')
    search_fields = ('nom', 'telephone', 'adresse')
    list_filter = ('nom',)
    
    def adresse_courte(self, obj):
        return obj.adresse[:50] + "..." if len(obj.adresse) > 50 else obj.adresse
    adresse_courte.short_description = "Adresse"
    
    fieldsets = (
        ('Informations client', {
            'fields': ('nom', 'telephone', 'adresse')
        }),
    )


class LivraisonInline(admin.TabularInline):
    model = Livraison
    extra = 0
    fields = ('client', 'reference_commande', 'quantite', 'horaire_estime', 'statut', 'produits', 'sacs')
    autocomplete_fields = ['client', 'produits', 'sacs']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client').prefetch_related('produits', 'sacs')


@admin.register(FeuilleDeRoute)
class FeuilleDeRouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'chauffeur', 'date_route', 'date_creation', 'statut', 'get_livraisons_count', 'qr_code_link')
    list_filter = ('statut', 'date_route', 'date_creation', 'chauffeur')
    search_fields = ('id', 'chauffeur__user__username', 'chauffeur__vehicule', 'chauffeur__immatriculation')
    date_hierarchy = 'date_route'
    inlines = [LivraisonInline]
    readonly_fields = ('token', 'qr_code', 'last_latitude', 'last_longitude', 'last_position_at')
    
    def get_livraisons_count(self, obj):
        count = obj.livraisons.count()
        return format_html('<span style="color: {};">{}</span>', 
                          'green' if count > 0 else 'red', count)
    get_livraisons_count.short_description = "Nb livraisons"
    
    def qr_code_link(self, obj):
        if obj.qr_code:
            return format_html('<a href="{}" target="_blank">📋 Voir QR</a>', obj.qr_code.url)
        return "Pas de QR"
    qr_code_link.short_description = "QR Code"
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('chauffeur', 'date_route', 'statut')
        }),
        ('Système', {
            'fields': ('token', 'qr_code'),
            'classes': ('collapse',)
        }),
        ('Géolocalisation', {
            'fields': ('last_latitude', 'last_longitude', 'last_position_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('reference_commande', 'client', 'feuille', 'quantite', 'statut', 'date_livraison', 'get_produits', 'get_sacs')
    list_filter = ('statut', 'date_livraison', 'feuille__chauffeur', 'produits', 'sacs')
    search_fields = ('reference_commande', 'client__nom', 'client__telephone', 'notes')
    date_hierarchy = 'date_livraison'
    autocomplete_fields = ['client', 'produits', 'sacs']
    readonly_fields = ('public_token', 'date_livraison')
    
    def get_produits(self, obj):
        produits = obj.produits.all()
        if produits:
            return ", ".join([p.nom for p in produits[:3]])
        return "Aucun"
    get_produits.short_description = "Produits"
    
    def get_sacs(self, obj):
        sacs = obj.sacs.all()
        if sacs:
            return ", ".join([s.nom for s in sacs[:3]])
        return "Aucun"
    get_sacs.short_description = "Sacs"
    
    fieldsets = (
        ('Informations de livraison', {
            'fields': ('feuille', 'client', 'reference_commande', 'quantite', 'horaire_estime', 'statut')
        }),
        ('Produits et sacs', {
            'fields': ('produits', 'sacs'),
            'description': 'Sélectionnez les produits et sacs à livrer'
        }),
        ('Preuves et documents', {
            'fields': ('preuve_photo', 'signature_client'),
            'classes': ('collapse',)
        }),
        ('Informations système', {
            'fields': ('public_token', 'date_livraison', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if obj.statut == 'livre' and not obj.date_livraison:
            from django.utils import timezone
            obj.date_livraison = timezone.now()
        super().save_model(request, obj, form, change)