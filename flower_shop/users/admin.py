from django.contrib import admin
from .models import Profile, TelegramActivationCode

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'telegram_username']
    search_fields = ['user__username', 'user__email', 'phone', 'city']

class TelegramActivationCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at']
    search_fields = ['user__username', 'code']

admin.site.register(Profile, ProfileAdmin)
admin.site.register(TelegramActivationCode, TelegramActivationCodeAdmin)