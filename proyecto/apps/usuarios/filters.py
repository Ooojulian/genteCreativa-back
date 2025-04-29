# backend/proyecto/apps/usuarios/filters.py (VERSIÓN CORREGIDA RECOMENDADA)

import django_filters
from .models import Usuario, Rol, Empresa # Asegúrate de importar tus modelos

class UsuarioFilter(django_filters.FilterSet):
    # --- Filtro 'rol' usando ModelChoiceFilter (espera ID) ---
    rol = django_filters.ModelChoiceFilter(
        field_name='rol',        # Campo ForeignKey en el modelo Usuario
        queryset=Rol.objects.all(), # Opciones posibles
        label='Filtrar por Rol (ID)'
    )
    # ---------------------------------------------------------

    # Filtro 'empresa' (ya estaba bien, espera ID)
    empresa = django_filters.ModelChoiceFilter(
        field_name='empresa',
        queryset=Empresa.objects.all(),
        label='Filtrar por Empresa (ID)'
    )

    # Filtro 'is_active' (ya estaba bien, espera true/false)
    is_active = django_filters.BooleanFilter(
        field_name='is_active',
        label='Filtrar por Estado Activo'
    )

    # --- UNA SOLA Clase Meta ---
    class Meta:
        model = Usuario
        # Lista los nombres de los filtros definidos arriba
        fields = ['rol', 'empresa', 'is_active']