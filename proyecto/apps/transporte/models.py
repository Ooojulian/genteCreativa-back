# backend/proyecto/apps/transporte/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import uuid
from django.conf import settings

class TipoVehiculo(models.Model):
    """Define los tipos de vehículos gestionables."""
    nombre = models.CharField(
        max_length=100,
        unique=True, # El nombre del tipo debe ser único
        verbose_name=_("Nombre del Tipo")
    )
    descripcion = models.TextField(
        blank=True, null=True,
        verbose_name=_("Descripción")
    )
    # Podrías añadir un campo 'codigo' o 'slug' si lo necesitas, ej: MOTO, PEQUENO
    # codigo = models.SlugField(max_length=20, unique=True, blank=True, null=True)

    class Meta:
        verbose_name = _("Tipo de Vehículo")
        verbose_name_plural = _("Tipos de Vehículo")
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Vehiculo(models.Model):
    placa = models.CharField(
        max_length=10,
        unique=True, # La placa debe ser única
        verbose_name=_("Placa"),
        help_text=_("Placa única del vehículo (Ej: AAA123)")
    )
    tipo = models.ForeignKey(
        TipoVehiculo, # Apunta al nuevo modelo
        on_delete=models.PROTECT, # Evita borrar un tipo si hay vehículos usándolo
        related_name='vehiculos', # Cómo acceder a los vehículos desde el tipo
        verbose_name=_("Tipo de Vehículo"),
        null=True
    )
    marca = models.CharField(
        max_length=100,
        blank=True, null=True, # Opcional
        verbose_name=_("Marca")
    )
    modelo = models.CharField(
        max_length=100,
        blank=True, null=True, # Opcional
        verbose_name=_("Modelo/Línea")
    )
    year = models.PositiveIntegerField(
        blank=True, null=True, # Opcional
        verbose_name=_("Año")
    )
    # Podrías añadir más campos como color, capacidad, SOAT, Tecnomecánica, etc.
    activo = models.BooleanField(
        default=True,
        verbose_name=_("¿Vehículo activo?"),
        help_text=_("Indica si el vehículo está disponible para ser asignado.")
    )

    class Meta:
        verbose_name = _("Vehículo")
        verbose_name_plural = _("Vehículos")
        ordering = ['placa'] # Ordenar por placa por defecto

    def __str__(self):
        return f"{self.placa} ({self.get_tipo_display()})" # Muestra placa y tipo


# --- Función para definir ruta de subida ---
def prueba_entrega_upload_path(instance, filename):
    # Guarda en: media/pruebas_entrega/<pedido_id>/<etapa>/<uuid>_<nombre_archivo>
    # Esto organiza las fotos por pedido y etapa.
    pedido_id = instance.pedido.id if instance.pedido else 'sin_pedido'
    etapa = instance.etapa if instance.etapa else 'sin_etapa'
    unique_id = uuid.uuid4()
    # Limpia el nombre del archivo por seguridad (opcional pero recomendado)
    # filename = "".join(c for c in filename if c.isalnum() or c in ('.', '_')).rstrip()
    return f'pruebas_entrega/{pedido_id}/{etapa}/{unique_id}_{filename}'

# --- Nuevo Modelo PruebaEntrega ---
class PruebaEntrega(models.Model):
    ETAPA_CHOICES = (
        ('INICIO', 'Inicio Viaje'),
        ('FIN', 'Fin Viaje'),
    )
    # --- NUEVO: Tipos específicos de foto ---
    TIPO_FOTO_CHOICES = (
        ('INICIO_GEN', 'Inicio - General'),      # Para fotos de inicio (puede ser una sola)
        ('FIN_MERC', 'Fin - Mercancía'),         # Foto de mercancía entregada
        ('FIN_REC', 'Fin - Receptor'),           # Foto de persona que recibe
        ('FIN_GEN', 'Fin - General'),            # Para Pasajeros/Renta si aplica
        # Puedes añadir más si necesitas (ej: FIN_DOC 'Fin - Documento Firmado')
    )

    pedido = models.ForeignKey(
        'PedidoTransporte',
        on_delete=models.CASCADE,
        related_name='pruebas_entrega',
        verbose_name=_("Pedido Asociado")
    )
    # --- NUEVO: Campo para tipo específico ---
    tipo_foto = models.CharField(
        max_length=10,
        choices=TIPO_FOTO_CHOICES,
        verbose_name=_("Tipo de Foto"),
        # default='INICIO_GEN' # Quitar default si quieres que siempre se especifique
    )
    # --- Campo etapa ahora es derivado y no editable ---
    etapa = models.CharField(
        max_length=10,
        choices=ETAPA_CHOICES,
        verbose_name=_("Etapa del Viaje"),
        editable=False # Se calcula en save()
    )
    foto = models.ImageField(
        upload_to=prueba_entrega_upload_path,
        verbose_name=_("Archivo de Foto")
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, # <-- USA settings.AUTH_USER_MODEL
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Subido por")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Fecha de Subida")
    )

    class Meta:
        verbose_name = _("Prueba de Entrega/Servicio")
        verbose_name_plural = _("Pruebas de Entrega/Servicio")
        ordering = ['pedido', 'timestamp'] # Ordenar por fecha

    def __str__(self):
        # Usar el display del tipo de foto para más claridad
        return f"Prueba {self.get_tipo_foto_display()} para Pedido {self.pedido_id}"

    # --- Sobrescribir save para calcular etapa ---
    def save(self, *args, **kwargs):
        # Asigna automáticamente la etapa correcta basado en el prefijo del tipo_foto
        if self.tipo_foto and self.tipo_foto.startswith('INICIO'):
            self.etapa = 'INICIO'
        elif self.tipo_foto and self.tipo_foto.startswith('FIN'):
            self.etapa = 'FIN'
        else:
            # Manejar caso por defecto o error si tipo_foto no es válido
            # Podrías lanzar un error o asignar una etapa por defecto
            self.etapa = 'FIN' # O asignar None si prefieres, pero el campo no lo permite
        super().save(*args, **kwargs) # Llama al método save original


# --- Modelo ConfirmacionCliente ---
class ConfirmacionCliente(models.Model):
    pedido = models.OneToOneField(
         'PedidoTransporte', # <-- Bien usar string
        on_delete=models.CASCADE,
        related_name='confirmacion_cliente',
        verbose_name=_("Pedido Asociado")
    )

    # Token único para la URL del formulario público
    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True # Buen índice para buscar por token
    )
    # Datos que llena el cliente
    nombre_receptor = models.CharField(max_length=255, verbose_name=_("Nombre de quien recibe"))
    cedula_receptor = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Cédula/ID de quien recibe (Opcional)"))
    # Guardaremos la firma como imagen base64 (texto largo)
    firma_imagen_base64 = models.TextField(blank=True, null=True, verbose_name=_("Firma (Data URL Base64)"))
    observaciones = models.TextField(blank=True, null=True, verbose_name=_("Observaciones del Cliente"))
    # Cuando se confirma
    fecha_confirmacion = models.DateTimeField(null=True, blank=True, verbose_name=_("Fecha de Confirmación"))

    class Meta:
        verbose_name = _("Confirmación del Cliente")
        verbose_name_plural = _("Confirmaciones de Clientes")

    def __str__(self):
        confirmado = "Confirmado" if self.fecha_confirmacion else "Pendiente"
        return f"Confirmación para Pedido {self.pedido_id} ({confirmado})"


class PedidoTransporte(models.Model):
    # --- CHOICES ---
    TIPO_VEHICULO_CHOICES = (
        ('MOTO', 'Motocicleta'),
        ('PEQUENO', 'Vehículo Pequeño (Automóvil)'),
        ('MEDIANO', 'Vehículo Mediano (Camioneta/SUV)'),
        ('GRANDE', 'Vehículo Grande (Furgón/Camión pequeño)'),
    )
    TIPO_SERVICIO_CHOICES = (
        ('SIMPLE', 'Envío Simple (Mercancía Punto a Punto)'),
        ('BODEGAJE_ENTRADA', 'Dejar Mercancía en Bodega'),
        ('BODEGAJE_SALIDA', 'Retirar Mercancía de Bodega'),
        ('PASAJEROS', 'Transporte de Pasajeros'),
        ('RENTA_VEHICULO', 'Renta Vehículo con Conductor'),
    )
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('en_curso', 'En Curso'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    )
    TIPO_TARIFA_PASAJERO_CHOICES = (
        ('TIEMPO', 'Por Tiempo'),
        ('DISTANCIA', 'Por Distancia'),
        # Podrías añadir 'FIJA' si aplica
    )

    # --- Campos Principales ---
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, # <-- USA settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        related_name='pedidos_cliente'
        # Puedes añadir limit_choices_to={'rol__nombre': 'cliente'} si quieres restringir en formularios
    )
    conductor = models.ForeignKey(
        settings.AUTH_USER_MODEL, # <-- USA settings.AUTH_USER_MODEL
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pedidos_conductor'
        # Puedes añadir limit_choices_to={'rol__nombre': 'conductor'}
    )
    # Origen/Destino ahora permiten nulos para casos como RENTA_VEHICULO
    origen = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Origen"))
    destino = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Destino"))
    descripcion = models.TextField(blank=True, verbose_name=_("Descripción/Notas Adicionales"))
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True, verbose_name=_("Fecha/Hora Inicio Real")) # Cuando el conductor inicia
    fecha_fin = models.DateTimeField(null=True, blank=True, verbose_name=_("Fecha/Hora Fin Real")) # Cuando el conductor finaliza

    tipo_servicio = models.CharField(
        verbose_name=_("Tipo de Servicio"),
        max_length=20, # Ajustar si claves son más largas
        choices=TIPO_SERVICIO_CHOICES,
        default='SIMPLE'
    )

    # --- Campos de Programación / Renta ---
    hora_recogida_programada = models.DateTimeField(
        verbose_name=_("Hora Inicio/Recogida Programada"), # Etiqueta más general
        null=True, blank=True
    )
    hora_entrega_programada = models.DateTimeField(
        verbose_name=_("Hora Fin/Entrega Programada"), # Etiqueta más general (puede ser opcional según el servicio)
        null=True, blank=True
    )
    tipo_vehiculo_requerido = models.CharField(
        verbose_name=_("Tipo de Vehículo Requerido/Rentado"), # Etiqueta general
        max_length=50,
        choices=TIPO_VEHICULO_CHOICES,
        null=True, blank=True
    )

    # --- Campos Específicos Mercancía / Bodega ---
    tiempo_bodegaje_estimado = models.CharField(
        verbose_name=_("Tiempo Bodegaje Estimado (Solo Entrada Bodega)"),
        max_length=100, blank=True, null=True
    )
    dimensiones_contenido = models.CharField(
        verbose_name=_("Dimensiones/Tamaño (Solo Mercancía)"),
        max_length=255, blank=True, null=True
    )

    # --- Campos Específicos Transporte de Pasajeros ---
    numero_pasajeros = models.PositiveIntegerField(
        verbose_name=_("Número de Pasajeros"),
        null=True, blank=True
    )
    tipo_tarifa_pasajero = models.CharField(
        verbose_name=_("Tipo Tarifa (Solo Pasajeros)"),
        max_length=10,
        choices=TIPO_TARIFA_PASAJERO_CHOICES,
        null=True, blank=True
    )
    duracion_estimada_horas = models.DecimalField(
        verbose_name=_("Duración Estimada (H) (Pasajeros por Tiempo)"),
        max_digits=5, decimal_places=2,
        null=True, blank=True
    )
    distancia_estimada_km = models.DecimalField(
        verbose_name=_("Distancia Estimada (Km) (Pasajeros por Distancia)"),
        max_digits=7, decimal_places=2,
        null=True, blank=True
    )

    requiere_fotos_inicio = models.BooleanField(default=True, verbose_name=_("¿Requiere Fotos al Iniciar?"))
    requiere_fotos_fin = models.BooleanField(default=True, verbose_name=_("¿Requiere Fotos al Finalizar?"))
    requiere_confirmacion_cliente = models.BooleanField(default=True, verbose_name=_("¿Requiere Confirmación Cliente (QR/Firma)?"))

    # Trackeo del estado de las validaciones (actualizado por otras vistas/procesos)
    fotos_inicio_completas = models.BooleanField(default=False, editable=False, verbose_name=_("Fotos Inicio OK?"))
    fotos_fin_completas = models.BooleanField(default=False, editable=False, verbose_name=_("Fotos Fin OK?"))
    confirmacion_cliente_realizada = models.BooleanField(default=False, editable=False, verbose_name=_("Confirmación Cliente OK?"))
    
    # --- FIN CAMPOS ESPECÍFICOS ---


    def __str__(self):
        # Muestra el tipo de servicio para identificarlo fácilmente
        return f'Pedido {self.id}: ({self.get_tipo_servicio_display()}) [{self.estado}]'

    # Validación simple a nivel de modelo (se puede expandir o mover al serializer)
    def clean(self):
        super().clean()
        # Ejemplo: Validación existente para BODEGAJE_ENTRADA
        if self.tipo_servicio == 'BODEGAJE_ENTRADA' and not self.tiempo_bodegaje_estimado:
            raise ValidationError({'tiempo_bodegaje_estimado': _("Debe indicar el tiempo estimado para Dejar en Bodega.")})
        # Ejemplo: Validación para que tiempo_bodegaje solo aplique a BODEGAJE_ENTRADA
        if self.tipo_servicio != 'BODEGAJE_ENTRADA' and self.tiempo_bodegaje_estimado:
            # Podrías simplemente limpiarlo aquí o lanzar error si prefieres que no se envíe
            # self.tiempo_bodegaje_estimado = None
             raise ValidationError({'tiempo_bodegaje_estimado': _("Tiempo estimado solo aplica para Dejar en Bodega.")})
        # Puedes añadir más validaciones aquí si son cruciales a nivel de modelo

# --- Modelo ItemPedido (SIN CAMBIOS, solo aplica a BODEGAJE_SALIDA) ---
class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        'PedidoTransporte', # <-- Bien usar string
        on_delete=models.CASCADE,
        related_name='items_pedido',
        verbose_name=_("Pedido Asociado")
    )
    producto = models.ForeignKey(
         'bodegaje.Producto', # <-- Mejor usar string aquí también por consistencia
        # Producto, # Si lo tenías así, cámbialo
        on_delete=models.PROTECT,
        verbose_name=_("Producto")
    )
    cantidad = models.PositiveIntegerField(
        verbose_name=_("Cantidad a Retirar/Mover")
    )

    class Meta:
        verbose_name = _("Item de Pedido (Solo Retiro Bodega)")
        verbose_name_plural = _("Items de Pedido (Solo Retiro Bodega)")
        unique_together = ('pedido', 'producto')

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre} (Pedido {self.pedido_id})'