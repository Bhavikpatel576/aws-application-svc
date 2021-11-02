from django.contrib import admin
from django.conf import settings

admin.site.site_header = getattr(settings, 'ADMIN_HEADER', 'CRM service admin')
