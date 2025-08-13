from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid




try:
    import qrcode
    from io import BytesIO
    from django.core.files.base import ContentFile
except ImportError:
    qrcode = None


class Chauffeur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telephone = models.CharField(max_length=15)
    vehicule = models.CharField(max_length=50, blank=True)
    immatriculation = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    class Meta:
        verbose_name = "Chauffeur"
        verbose_name_plural = "Chauffeurs"


class Client(models.Model):
    nom = models.CharField(max_length=100)
    adresse = models.TextField()
    telephone = models.CharField(max_length=15)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"


class Produit(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom du produit")
    description = models.TextField(blank=True, verbose_name="Description")
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix unitaire (€)")
    actif = models.BooleanField(default=True, verbose_name="Produit actif")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        return f"{self.nom} - {self.prix_unitaire}€"

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['nom']


class Sac(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom du sac")
    description = models.TextField(blank=True, verbose_name="Description")
    capacite = models.CharField(max_length=50, blank=True, verbose_name="Capacité")
    couleur = models.CharField(max_length=30, blank=True, verbose_name="Couleur")
    actif = models.BooleanField(default=True, verbose_name="Sac actif")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    def __str__(self):
        return f"{self.nom} - {self.couleur}"

    class Meta:
        verbose_name = "Sac"
        verbose_name_plural = "Sacs"
        ordering = ['nom']


STATUTS_FEUILLE = [
    ('planifie', 'Planifié'),
    ('en_route', 'En route'),
    ('terminee', 'Terminée'),
    ('probleme', 'Problème'),
]


class FeuilleDeRoute(models.Model):
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.CASCADE, verbose_name="Chauffeur")
    date_creation = models.DateField(auto_now_add=True, verbose_name="Date de création")
    date_route = models.DateField(null=True, blank=True, verbose_name="Date de route")
    statut = models.CharField(max_length=20, choices=STATUTS_FEUILLE, default='planifie', verbose_name="Statut")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="QR Code")

    # Dernière position connue
    last_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Latitude")
    last_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Longitude")
    last_position_at = models.DateTimeField(null=True, blank=True, verbose_name="Dernière position")

    def __str__(self):
        return f"Feuille {self.id} - {self.chauffeur}"

    def get_driver_url(self):
        return f"/livraison/feuille/{self.token}/"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if (creating or not self.qr_code) and qrcode:
            img = qrcode.make(self.get_driver_url())
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            filename = f"feuille_{self.pk}.png"
            self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
            super().save(update_fields=['qr_code'])

    class Meta:
        verbose_name = "Feuille de route"
        verbose_name_plural = "Feuilles de route"


STATUTS_LIVRAISON = [
    ('en_cours', 'En cours'),
    ('livre', 'Livré'),
    ('probleme', 'Problème'),
]


class Livraison(models.Model):
    feuille = models.ForeignKey(FeuilleDeRoute, on_delete=models.CASCADE, related_name="livraisons", verbose_name="Feuille de route")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Client")
    reference_commande = models.CharField(max_length=50, verbose_name="Référence commande")
    quantite = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    horaire_estime = models.TimeField(blank=True, null=True, verbose_name="Horaire estimé")
    statut = models.CharField(max_length=20, choices=STATUTS_LIVRAISON, default='en_cours', verbose_name="Statut")
    preuve_photo = models.ImageField(upload_to="preuves/", blank=True, null=True, verbose_name="Preuve photo")
    signature_client = models.ImageField(upload_to="signatures/", blank=True, null=True, verbose_name="Signature client")
    date_livraison = models.DateTimeField(blank=True, null=True, verbose_name="Date de livraison")
    public_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Nouveaux champs pour produits et sacs
    produits = models.ManyToManyField(Produit, blank=True, verbose_name="Produits")
    sacs = models.ManyToManyField(Sac, blank=True, verbose_name="Sacs")
    notes = models.TextField(blank=True, verbose_name="Notes de livraison")

    def __str__(self):
        return f"Livraison {self.reference_commande} - {self.client.nom}"

    def get_public_url(self):
        return f"/livraison/track/{self.public_token}/"

    class Meta:
        verbose_name = "Livraison"
        verbose_name_plural = "Livraisons"