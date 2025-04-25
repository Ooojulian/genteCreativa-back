# backend/proyecto/apps/bodegaje/admin.py
from django.contrib import admin
# Asegúrate de importar los tres modelos
from .models import Producto, Ubicacion, Inventario, MovimientoInventario

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sku', 'descripcion')
    search_fields = ('nombre', 'sku')

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'ubicacion', 'cantidad', 'empresa', 'fecha_actualizacion')
    list_filter = ('empresa', 'ubicacion', 'producto')
    search_fields = ('producto__nombre', 'ubicacion__nombre', 'empresa__nombre')
    list_select_related = ('producto', 'ubicacion', 'empresa') # Optimiza carga

# --- REGISTRO DEL HISTORIAL ---
@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'tipo_movimiento', 'producto', 'ubicacion', 'empresa', 'cantidad_cambio', 'cantidad_nueva', 'usuario')
    list_filter = ('tipo_movimiento', 'empresa', 'ubicacion', 'producto', 'usuario')
    search_fields = ('producto__nombre', 'ubicacion__nombre', 'empresa__nombre', 'usuario__cedula', 'motivo')
    list_select_related = ('producto', 'ubicacion', 'empresa', 'usuario')
    readonly_fields = ('timestamp',) # La fecha se pone sola
    list_per_page = 50 # Muestra más por página
# --- FIN REGISTRO ---