# backend/proyecto/apps/bodegaje/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Producto, Ubicacion, MovimientoInventario
from .middleware import get_current_user # Importa la función helper

# --- Señales para Producto ---

@receiver(post_save, sender=Producto)
def log_producto_guardado(sender, instance, created, **kwargs):
    """Registra la creación o modificación de un Producto."""
    current_user = get_current_user()
    tipo = 'PROD_CREADO' if created else 'PROD_MODIFICADO'
    motivo = f"Producto '{instance.nombre}' (SKU: {instance.sku}) {'creado' if created else 'modificado'}."

    # Opcional: Detallar qué campos cambiaron (más complejo)
    # if not created:
    #    # Necesitarías comparar con el estado pre_save o implementar lógica de rastreo
    #    motivo += " [Campos modificados: ...]" # Placeholder

    MovimientoInventario.objects.create(
        producto=instance,
        tipo_movimiento=tipo,
        motivo=motivo,
        usuario=current_user if current_user and current_user.is_authenticated else None,
        # Los campos de cantidad e inventario/empresa/ubicación quedan en None/0
        cantidad_anterior=None,
        cantidad_nueva=None,
        cantidad_cambio=0,
        inventario=None,
        ubicacion=None,
        empresa=None,
    )

@receiver(post_delete, sender=Producto)
def log_producto_eliminado(sender, instance, **kwargs):
    """Registra la eliminación de un Producto."""
    current_user = get_current_user()
    motivo = f"Producto ID {instance.id} ('{instance.nombre}', SKU: {instance.sku}) eliminado."

    MovimientoInventario.objects.create(
        # Guarda el ID y nombre en el motivo, ya que la FK será NULL pronto
        producto=None, # Ya no existe para FK
        tipo_movimiento='PROD_ELIMINADO',
        motivo=motivo,
        usuario=current_user if current_user and current_user.is_authenticated else None,
        cantidad_anterior=None,
        cantidad_nueva=None,
        cantidad_cambio=0,
        inventario=None,
        ubicacion=None,
        empresa=None,
    )

# --- Señales para Ubicacion ---

@receiver(post_save, sender=Ubicacion)
def log_ubicacion_guardada(sender, instance, created, **kwargs):
    """Registra la creación o modificación de una Ubicacion."""
    current_user = get_current_user()
    tipo = 'UBI_CREADA' if created else 'UBI_MODIFICADA'
    motivo = f"Ubicación '{instance.nombre}' {'creada' if created else 'modificada'}."

    # Opcional: Detallar campos modificados

    MovimientoInventario.objects.create(
        ubicacion=instance,
        tipo_movimiento=tipo,
        motivo=motivo,
        usuario=current_user if current_user and current_user.is_authenticated else None,
        cantidad_anterior=None,
        cantidad_nueva=None,
        cantidad_cambio=0,
        inventario=None,
        producto=None,
        empresa=None,
    )

@receiver(post_delete, sender=Ubicacion)
def log_ubicacion_eliminada(sender, instance, **kwargs):
    """Registra la eliminación de una Ubicacion."""
    current_user = get_current_user()
    motivo = f"Ubicación ID {instance.id} ('{instance.nombre}') eliminada."

    MovimientoInventario.objects.create(
        ubicacion=None, # Ya no existe
        tipo_movimiento='UBI_ELIMINADA',
        motivo=motivo,
        usuario=current_user if current_user and current_user.is_authenticated else None,
        cantidad_anterior=None,
        cantidad_nueva=None,
        cantidad_cambio=0,
        inventario=None,
        producto=None,
        empresa=None,
    )