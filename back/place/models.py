
from django.db import models
from django.utils import timezone
from back.common.models import User

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
    address = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    menu_or_ticket_info = models.JSONField(null=True, blank=True)
    price = models.CharField(max_length=50, null=True, blank=True)
    translated_reviews = models.JSONField(null=True, blank=True)
    reference_urls = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('name', 'language')

    def __str__(self):
        return f"{self.name} - {self.language}"


class PlaceLog(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    language = models.CharField(max_length=255, null=True, blank=True)
    called_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} / {self.address} at {self.called_at}"
    
class UserCategory(models.Model):
    user = models.ForeignKey(User, related_name="userCategories", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    color = models.TextField(null=True, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.user.email} - {self.name}"

class SavedPlace(models.Model):
    category = models.ForeignKey(UserCategory, related_name="savedPlaces", on_delete=models.CASCADE)
    place_id = models.CharField(max_length=100)
    place_name = models.CharField(max_length=255)
    address_name = models.CharField(max_length=255, null=True, blank=True)
    road_address_name = models.CharField(max_length=255, null=True, blank=True)
    road_address_name_en = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    category_name = models.CharField(max_length=255, null=True, blank=True)
    category_name_en = models.CharField(max_length=255, null=True, blank=True)
    place_url = models.URLField(null=True, blank=True)
    category_group_code = models.CharField(max_length=50, null=True, blank=True)
    x = models.CharField(max_length=50, null=True, blank=True)
    y = models.CharField(max_length=50, null=True, blank=True)
    lat = models.CharField(max_length=50, null=True, blank=True)
    lng = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('category', 'place_id')

    def __str__(self):
        return f"{self.place_name} - {self.category.name}"


class PlaceInfoChangeRequest(models.Model):
    user = models.ForeignKey(User, related_name="placeInfoChangeRequests", on_delete=models.CASCADE)
    place_info = models.ForeignKey(PlaceInfo, related_name="placeInfoChangeRequests", on_delete=models.CASCADE)
    new_value = models.JSONField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.place_info.name}"

class PlaceReviewByUser(models.Model):
    user = models.ForeignKey(User, related_name="placeInfoReviews", on_delete=models.CASCADE)
    place_info = models.ForeignKey(PlaceInfo, related_name="placeInfoReviews", on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)
    images = models.JSONField(null=True, blank=True)
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.place_info.name}"

class PlaceInfoReviewByUserReport(models.Model):
    place_review = models.ForeignKey(PlaceReviewByUser, related_name="placeReviewByUserReports", on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.place_review and self.place_review.place_info:
            return f"{self.place_review.place_info.name}"
        return "(deleted review)"