# backend/proyecto/apps/usuarios/urls.py (MODIFICADO)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Asegúrate que estas vistas SÍ estén definidas en usuarios/views.py
from .views import UsuarioViewSet, EmpresaViewSet, MinimalAuthTestView, RolListView # Añade MinimalAuthTestView

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'empresas', EmpresaViewSet, basename='empresa')

urlpatterns = [
    # Incluye las rutas del router bajo el prefijo /api/gestion/
    path('', include(router.urls)),
    # Ruta de prueba para autenticación básica
    path('test-auth/', MinimalAuthTestView.as_view(), name='test-auth'),
    path('roles/', RolListView.as_view(), name='rol-list'),
]