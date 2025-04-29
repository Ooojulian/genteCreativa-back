# backend/proyecto/apps/bodegaje/filters.py (NUEVO ARCHIVO)

import django_filters
from .models import Inventario, Producto, Ubicacion # Importa modelos de esta app
from apps.usuarios.models import Empresa # Importa Empresa desde usuarios

class InventarioFilter(django_filters.FilterSet):
    # Filtro para Producto (espera ?producto=ID)
    producto = django_filters.ModelChoiceFilter(
        queryset=Producto.objects.all(),
        field_name='producto',
        label='Filtrar por Producto (ID)'
    )

    # Filtro para Ubicacion (espera ?ubicacion=ID)
    ubicacion = django_filters.ModelChoiceFilter(
        queryset=Ubicacion.objects.all(),
        field_name='ubicacion',
        label='Filtrar por Ubicación (ID)'
    )

    # Filtro para Empresa (espera ?empresa=ID)
    empresa = django_filters.ModelChoiceFilter(
        queryset=Empresa.objects.all(),
        field_name='empresa',
        label='Filtrar por Empresa (ID)'
    )

    class Meta:
        model = Inventario
        # Define los campos por los que se puede filtrar
        # Deben coincidir con los nombres de los filtros definidos arriba
        fields = ['producto', 'ubicacion', 'empresa']