"""api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings
from django.http import JsonResponse
from django.contrib.admin.sites import AdminSite
from django.views.generic import TemplateView


def trigger_error(request):
    # NOTE: division by zero
    return 1 / 0

def health_check(request):
    return JsonResponse({"success": True})

urlpatterns = [
    path('health-check', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    path('', include('app.urls', namespace='app')),
    path('sentry-debug/', trigger_error),
    path('googlef37c7f7307a71f88.html', TemplateView.as_view(
        template_name='googlef37c7f7307a71f88.html')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

AdminSite.site_header = 'Bynde Admin Panel'
AdminSite.site_title = 'Bynde'
AdminSite.index_title = ''
