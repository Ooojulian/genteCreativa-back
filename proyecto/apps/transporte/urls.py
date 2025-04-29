# backend/proyecto/apps/transporte/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PedidoTransporteCreateView, # La vista que acabamos de revisar
    PedidosConductorList,
    HistorialMesConductorList,
    HistorialMesGeneralList,
    PedidoTransporteViewSet,
    SimplePedidoTestView,
    ClientePedidoSimpleCreateView,
    PruebaEntregaUploadView,
    ConfirmacionClienteView,
    HistorialMesClienteList,
    RemisionPDFView,
    VehiculoViewSet,
    TipoVehiculoViewSet
)
from .views import GenerarQRDataView

router = DefaultRouter()
router.register(r'pedidos', PedidoTransporteViewSet, basename='pedido-transporte') # Para Jefes/Admin
router.register(r'vehiculos', VehiculoViewSet, basename='vehiculo')
router.register(r'tipos-vehiculo', TipoVehiculoViewSet, basename='tipovehiculo')


urlpatterns = [
    path('pedidos/<int:pk>/remision/', RemisionPDFView.as_view(), name='pedido-remision-pdf'),
    # Esperar post para recibir la confirmación del cliente
    path('confirmar/<uuid:token>/', ConfirmacionClienteView.as_view(), name='confirmar-cliente'),

    # Espera POST a /api/transporte/pedidos/<pedido_pk>/subir_prueba/
    path('pedidos/<int:pedido_pk>/subir_prueba/', PruebaEntregaUploadView.as_view(), name='subir-prueba-entrega'),
    
    # Espera GET a /api/transporte/pedidos/<pedido_pk>/qr_data/
    path('pedidos/<int:pedido_pk>/qr_data/', GenerarQRDataView.as_view(), name='pedido-qr-data'),

    # --- URL para la gestión general de Jefes/Admin ---
    path('', include(router.urls)),

    # --- URL DEDICADA para que CLIENTE cree pedido ---
    path('pedidos/crear/', PedidoTransporteCreateView.as_view(), name='pedido-crear-cliente'),

    # Para que cliente vea el historial de sus pedidos
     path('mi_historial/', HistorialMesClienteList.as_view(), name='historial-mes-cliente'),
    

    # --- URLs específicas para Conductor ---
    path('mis_pedidos/', PedidosConductorList.as_view(), name='mis-pedidos-conductor'),
    path('historial_mes_conductor/', HistorialMesConductorList.as_view(), name='historial-mes-conductor'),

    # --- URL específica para historial general Jefe/Admin ---
    path('historial_mes/', HistorialMesGeneralList.as_view(), name='historial-mes-general'),
    path('simple-test/', SimplePedidoTestView.as_view(), name='simple-test-pedido'),
    path('pedidos/nuevo/', ClientePedidoSimpleCreateView.as_view(), name='pedido-crear-simple-cliente'),
]