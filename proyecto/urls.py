# backend/proyecto/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Importar settings
from django.conf.urls.static import static # Importar static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.usuarios.auth_urls')), 
    path('api/gestion/', include('apps.usuarios.urls')), 
    path('api/transporte/', include('apps.transporte.urls')),
    path('api/bodegaje/', include('apps.bodegaje.urls')),
]

# Servir archivos de media durante el desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# --- FIN AÑADIR ---