from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet, UbicacionViewSet, InventarioViewSet, HistorialInventarioView

router = DefaultRouter()
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'ubicaciones', UbicacionViewSet, basename='ubicacion')
router.register(r'inventario', InventarioViewSet, basename='inventario') # <-- Importante

urlpatterns = [
    path('', include(router.urls)), # <-- Importante
    path('historial/', HistorialInventarioView.as_view(), name='historial-inventario'),
]