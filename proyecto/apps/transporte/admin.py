from django.contrib import admin
from .models import PedidoTransporte  # Importa tu modelo

# Registra el modelo para que aparezca en el admin
admin.site.register(PedidoTransporte)
