from django.db import models
from apps.usuarios.models import Empresa
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class Producto(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True) #  SKU (Stock Keeping Unit) - Identificador único del producto

    def __str__(self):
        return self.nombre
    
class Ubicacion(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    def __str__(self):
        return self.nombre

class Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE, # Si se borra la empresa, se borra su inventario asociado
        related_name='inventario',
        verbose_name=_("Empresa Propietaria"),
        blank=True,  # Permitir que el campo esté vacío en formularios
        null=True    # Permitir valores nulos en la base de datos
    )

    fecha_creacion = models.DateTimeField(
        default=timezone.now, # Establece la fecha/hora actual al crear
        editable=False,       # No se puede editar desde el admin/formularios
        verbose_name=_("Fecha Creación Registro")
    )

    def __str__(self):
        # Verifica si hay empresa antes de acceder a su nombre
        nombre_empresa = self.empresa.nombre if self.empresa else "[Sin Empresa]"
        return f'{self.producto.nombre} ({self.cantidad}) @ {self.ubicacion.nombre} [{nombre_empresa}]'
    
    class Meta:
        # Evita duplicados: Mismo producto en misma ubicación para misma empresa
        unique_together = ('producto', 'ubicacion', 'empresa')
        verbose_name = _("Inventario")
        verbose_name_plural = _("Inventarios")

# --- NUEVO MODELO PARA HISTORIAL ---
class MovimientoInventario(models.Model):
    TIPO_MOVIMIENTO_CHOICES = (
        # Tipos existentes
        ('CREACION', 'Creación Inicial Inventario'),
        ('ACTUALIZACION', 'Actualización Cantidad Inventario'),
        ('ELIMINACION', 'Eliminación Registro Inventario'),
        ('AJUSTE_POS', 'Ajuste Positivo Inventario'),
        ('AJUSTE_NEG', 'Ajuste Negativo Inventario'),
        # Nuevos tipos para Productos
        ('PROD_CREADO', 'Producto Creado'),
        ('PROD_MODIFICADO', 'Producto Modificado'),
        ('PROD_ELIMINADO', 'Producto Eliminado'),
        # Nuevos tipos para Ubicaciones
        ('UBI_CREADA', 'Ubicación Creada'),
        ('UBI_MODIFICADA', 'Ubicación Modificada'),
        ('UBI_ELIMINADA', 'Ubicación Eliminada'),
    )

    # Relación al inventario afectado (puede ser NULL si se borró el inventario)
    inventario = models.ForeignKey(Inventario, on_delete=models.SET_NULL, null=True, blank=True, related_name='historial')
    # Guardamos referencias a Producto, Ubicacion, Empresa por si se borra el Inventario
    # Usamos SET_NULL para no perder el historial si se borra un producto/ubicacion/empresa
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.SET_NULL, null=True, blank=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Empresa Cliente"))

    tipo_movimiento = models.CharField(max_length=15, choices=TIPO_MOVIMIENTO_CHOICES)
    cantidad_anterior = models.IntegerField(null=True, blank=True) # Permite NULL
    cantidad_nueva = models.IntegerField(null=True, blank=True)    # Permite NULL
    cantidad_cambio = models.IntegerField(default=0) # <- Añadir default=0, sigue siendo no nulo
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Referencia al modelo Usuario de Django
        on_delete=models.SET_NULL, # No borrar historial si se borra el usuario
        null=True, blank=True,     # Permite acciones anónimas o si se borra el user
        verbose_name=_("Usuario Responsable")
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha y Hora"))
    motivo = models.TextField(blank=True, null=True, verbose_name=_("Detalle del Cambio / Motivo")) # Más genérico
    
    class Meta:
        verbose_name = _("Movimiento/Log") # Nombre más general
        verbose_name_plural = _("Historial General Bodegaje")
        ordering = ['-timestamp']

    def __str__(self):
        # String más informativo para diferentes tipos
        if self.tipo_movimiento.startswith('PROD_'):
             prod_info = f"Prod ID {self.producto_id}" if self.producto_id else "Producto ?"
             return f"{self.get_tipo_movimiento_display()} - {prod_info} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
        elif self.tipo_movimiento.startswith('UBI_'):
            ubi_info = f"Ubi ID {self.ubicacion_id}" if self.ubicacion_id else "Ubicación ?"
            return f"{self.get_tipo_movimiento_display()} - {ubi_info} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
        else:
             # Formato existente para movimientos de inventario
             emp_info = f"Emp ID {self.empresa_id}" if self.empresa_id else "Global"
             return f"{self.get_tipo_movimiento_display()} - Prod ID {self.producto_id} - Ubi ID {self.ubicacion_id} - {emp_info} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"

# --- FIN NUEVO MODELO ---