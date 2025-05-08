from django.contrib import admin
from back.place.models import (
  Category, RegionName,
  CategoryLog, RegionLog,
  PlaceInfo, PlaceLog
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
