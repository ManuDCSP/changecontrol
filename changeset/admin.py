from django.contrib import admin
from .models import ChangeSet


class ChangesetAdmin(admin.ModelAdmin):
    list_display = ('reference', 'status')


# Register your models here.
admin.site.register(ChangeSet, ChangesetAdmin)