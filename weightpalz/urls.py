from django.contrib import admin
from django.urls import include, path

from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
        # Install as app (PWA)
    path('manifest.webmanifest', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='sw'),
]