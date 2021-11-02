import cas.views
from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic.base import RedirectView
from django.views.static import serve

from api.v1_0_0.views.certified_partner_redirect_views import CertifiedPartnerRedirectViewSet

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/login/', cas.views.login, name='login'),
    path('account/logout/', cas.views.logout, name='logout'),
    path('api/', include('api.urls')),
    path(r'agent/<str:phone>', CertifiedPartnerRedirectViewSet.as_view({'get': 'retrieve'})),
    path('', RedirectView.as_view(url='/admin')),
    re_path(r'^static/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT
    }),
]
