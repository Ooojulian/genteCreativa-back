from rest_framework import serializers
from .models import PedidoTransporte
from apps.usuarios.models import Usuario  # Importa el *modelo* Usuario, no el serializador
# O BIEN
# from ..usuarios.models import Usuario # Importacion relativa


class PedidoTransporteSerializer(serializers.ModelSerializer):
    # Usa StringRelatedField para mostrar representaciones de texto:
    cliente = serializers.StringRelatedField(read_only=True)
    conductor = serializers.StringRelatedField(read_only=True)

    # Y *strings* para los queryset en los PrimaryKeyRelatedField:
    cliente_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(rol__nombre='cliente'),
        source='cliente',
        write_only=True  # Agregamos para que no se muestre
    )
    conductor_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(rol__nombre='conductor'),
        source='conductor',
        required=False,
        allow_null=True,
        write_only=True  # Agregamos para que no se muestre
    )

    class Meta:
        model = PedidoTransporte
        fields = '__all__'
