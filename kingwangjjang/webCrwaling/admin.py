# admin.py

from django.contrib import admin
from .models import Daily, RealTime

admin.site.register(Daily)
admin.site.register(RealTime)
