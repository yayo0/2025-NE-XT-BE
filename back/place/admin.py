from django.contrib import admin
from back.place.models import (
  Category, RegionName,
  CategoryLog, RegionLog,
  PlaceInfo, PlaceLog,
  UserCategory, SavedPlace,
  PlaceInfoChangeRequest,
  PlaceReviewByUser,
  PlaceInfoReviewByUserReport
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
  list_display = [field.name for field in Category._meta.fields]
  search_fields = ['korean', 'english']
  ordering = ['korean']


@admin.register(RegionName)
class RegionNameAdmin(admin.ModelAdmin):
  list_display = [field.name for field in RegionName._meta.fields]
  search_fields = ['english', 'korean']
  ordering = ['english']


@admin.register(CategoryLog)
class CategoryLogAdmin(admin.ModelAdmin):
  list_display = [field.name for field in CategoryLog._meta.fields]
  search_fields = ['korean']
  list_filter = ['called_at']
  ordering = ['-id']


@admin.register(RegionLog)
class RegionLogAdmin(admin.ModelAdmin):
  list_display = [field.name for field in RegionLog._meta.fields]
  search_fields = ['english']
  list_filter = ['called_at']
  ordering = ['-id']


@admin.register(PlaceInfo)
class PlaceInfoAdmin(admin.ModelAdmin):
  list_display = [field.name for field in PlaceInfo._meta.fields]
  search_fields = ['name', 'address', 'title', 'category']
  list_filter = ['category']
  ordering = ['-id']


@admin.register(PlaceLog)
class PlaceLogAdmin(admin.ModelAdmin):
  list_display = [field.name for field in PlaceLog._meta.fields]
  search_fields = ['name', 'address']
  list_filter = ['called_at']
  ordering = ['-id']

@admin.register(UserCategory)
class UserCategoryAdmin(admin.ModelAdmin):
  list_display = [field.name for field in UserCategory._meta.fields]
  search_fields = ['name']
  ordering = ['-id']

@admin.register(SavedPlace)
class SavedPlaceAdmin(admin.ModelAdmin):
  list_display = [field.name for field in SavedPlace._meta.fields]
  search_fields = ['place_name']
  ordering = ['-id']

@admin.register(PlaceInfoChangeRequest)
class PlaceInfoChangeRequestAdmin(admin.ModelAdmin):
  list_display = [field.name for field in PlaceInfoChangeRequest._meta.fields]
  search_fields = ['user__email', 'place_info__name']
  ordering = ['-id']

@admin.register(PlaceReviewByUser)
class PlaceReviewByUserAdmin(admin.ModelAdmin):
  list_display = [field.name for field in PlaceReviewByUser._meta.fields]
  search_fields = ['user__email', 'place_info__name']
  ordering = ['-id']

@admin.register(PlaceInfoReviewByUserReport)
class PlaceInfoReviewByUserReportAdmin(admin.ModelAdmin):
  list_display = [field.name for field in PlaceInfoReviewByUserReport._meta.fields]
  search_fields = ['place_review__place_info__name']
  ordering = ['-id']