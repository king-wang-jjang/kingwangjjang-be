# admin.py

from django.contrib import admin
from .communityWebsite.models import Daily, RealTime

admin.site.register(Daily)
admin.site.register(RealTime)
