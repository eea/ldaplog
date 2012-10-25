from django.contrib import admin
from ldap_mon import models


class UserAdmin(admin.ModelAdmin):

    search_fields = ['username']


class ServerAdmin(admin.ModelAdmin):

    search_fields = ['host']


class LogAdmin(admin.ModelAdmin):

    search_fields = ['user', 'server', 'date']



admin.site.register(models.User, UserAdmin)

admin.site.register(models.Server, ServerAdmin)

admin.site.register(models.Log, LogAdmin)