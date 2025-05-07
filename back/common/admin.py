from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from back.common.models import User, EmailVerification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
  list_display = [field.name for field in User._meta.fields if field.name not in ['password']]
  list_filter = ['is_staff', 'is_superuser', 'is_active']
  search_fields = ['email', 'name']
  ordering = ['email']



@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
  list_display = [field.name for field in EmailVerification._meta.fields]
  list_filter = ['purpose', 'created_at']
  search_fields = ['email', 'code', 'token']
  ordering = ['-created_at']

  def is_expired(self, obj):
    return obj.is_expired()
  is_expired.boolean = True
  is_expired.short_description = 'Expired?'
