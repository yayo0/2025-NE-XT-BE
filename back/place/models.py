
from django.db import models
from django.utils import timezone
# Create your models here.
class Category(models.Model):
    korean = models.CharField(max_length=255, unique=True)
    english = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.korean} → {self.english}"

class RegionName(models.Model):
    korean = models.CharField(max_length=100, unique=True)
    english = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.english} -> {self.korean}"
    
class CategoryLog(models.Model):
    korean = models.CharField(max_length=255)
    called_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.korean} at {self.called_at}"

class RegionLog(models.Model):
    english = models.CharField(max_length=255)
    called_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.english} at {self.called_at}"

class PlaceInfo(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    language = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    menu_or_ticket_info = models.JSONField(null=True, blank=True)
    price = models.CharField(max_length=50, null=True, blank=True)
    translated_reviews = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('name', 'address')

    def __str__(self):
        return f"{self.name} - {self.address}"


class PlaceLog(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    language = models.CharField(max_length=255, null=True, blank=True)
    called_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} / {self.address} at {self.called_at}"
