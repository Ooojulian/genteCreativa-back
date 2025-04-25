# backend/proyecto/apps/usuarios/serializers.py
from rest_framework import serializers
from .models import Usuario, Rol, Empresa  # Importa los modelos necesarios
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.translation import gettext_lazy as _ # Importa para mensajes de error

# Serializer simple para mostrar info básica de Empresa (solo lectura anidada)
class EmpresaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ('id', 'nombre')

# Serializer para el Token de Login que incluye datos del Usuario
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Opcional: añadir claims personalizados al token
        # token['nombre_completo'] = user.get_full_name()
        return token

    def validate(self, attrs):
        data = super().validate(attrs) # Obtiene tokens access y refresh
        # Usa UsuarioSerializer para obtener los datos del usuario
        # ¡Asegúrate que UsuarioSerializer esté definido ANTES de esta clase!
        serializer = UsuarioSerializer(self.user)
        user_data = serializer.data
        # Añade los datos del usuario a la respuesta del login
        data['user'] = user_data
        return data

# Serializer para el modelo Rol
class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'

# Serializer principal para el modelo Usuario (CRUD y lectura en Login)
class UsuarioSerializer(serializers.ModelSerializer):
    # --- Campos de Solo Lectura (para mostrar datos relacionados) ---
    rol = RolSerializer(read_only=True)
    empresa = EmpresaSimpleSerializer(read_only=True)

    # --- Campos de Solo Escritura (para recibir IDs al crear/editar) ---
    rol_id = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.all(),
        source='rol',          # Mapea al campo 'rol' del modelo
        write_only=True
        # required=True por defecto, lo cual está bien para rol
    )
    # ¡Eliminamos la línea duplicada de rol_id que tenías!

    empresa_id = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(),
        source='empresa',       # Mapea al campo 'empresa' del modelo
        write_only=True,
        required=False,         # No requerido para roles internos
        allow_null=True         # Permite enviar null
    )
    # --- Fin Campos ---

    class Meta:
        model = Usuario
        # --- CORRECCIÓN: Incluir 'empresa_id' en la lista ---
        fields = (
            'id', 'username', 'email', 'nombre', 'apellido', 'cedula',
            'rol', 'rol_id',           # Rol (lectura) y Rol ID (escritura)
            'empresa', 'empresa_id',   # Empresa (lectura) y Empresa ID (escritura) <-- AÑADIDO 'empresa_id'
            'password', 'is_active', 'is_staff'
        )
        # --- FIN CORRECCIÓN ---
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}}, # Oculta en API y hashea
            'is_active': {'read_only': True}, # Generalmente controlado por admin/lógica
            'is_staff': {'read_only': True}   # Generalmente controlado por admin
        }

    # Validación personalizada para la lógica rol/empresa
    def validate(self, data):
        # data contiene los objetos ya validados por los _id fields si se enviaron
        rol = data.get('rol') # Objeto Rol (o None si no se envió rol_id)
        empresa = data.get('empresa') # Objeto Empresa (o None si no se envió empresa_id o fue null)

        # Si estamos editando (instance existe) y no se envió rol_id, usamos el rol actual
        if self.instance and 'rol' not in data:
             rol = self.instance.rol
        # Si estamos editando y no se envió empresa_id, usamos la empresa actual
        if self.instance and 'empresa' not in data:
             empresa = self.instance.empresa

        # Aplicar la regla de negocio
        if rol:
            if rol.nombre == 'cliente':
                if not empresa:
                    # Si el rol es cliente, DEBE tener empresa
                    raise serializers.ValidationError({"empresa_id": _("Los usuarios con rol 'cliente' deben tener una empresa asignada.")})
            else: # Si el rol NO es cliente (conductor, jefe, admin...)
                if empresa:
                    # NO deben tener empresa asignada
                    raise serializers.ValidationError({"empresa_id": _(f"Los usuarios con rol '{rol.nombre}' no deben tener una empresa asignada (debe ser nulo).")})
        # Considera el caso donde el rol es None (si eso es posible en tu lógica)
        # elif empresa:
        #    raise serializers.ValidationError({"empresa_id": _("No se puede asignar una empresa si no se ha definido un rol.")})

        return data

    # Método para hashear contraseña al crear
    def create(self, validated_data):
        # validated_data ya contiene los objetos Rol y Empresa correctos
        password = validated_data.pop('password') # Extrae password para hashear
        user = Usuario(**validated_data)
        user.set_password(password) # Hashea la contraseña

        # Genera username si está vacío y hay email
        if not user.username and user.email:
             user.username = user.email

        user.save()
        return user

    # Método para hashear contraseña si se actualiza
    def update(self, instance, validated_data):
        # Si se envía una nueva contraseña en la petición PATCH/PUT...
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password) # Hashea la nueva contraseña

        # Genera username si se actualiza y queda vacío pero hay email
        # email puede venir de validated_data (si se cambió) o del instance (si no)
        if 'username' in validated_data and not validated_data['username'] \
           and validated_data.get('email', instance.email):
             validated_data['username'] = validated_data.get('email', instance.email)

        # Actualiza los demás campos usando el método padre
        return super().update(instance, validated_data)


# Serializer completo para gestionar Empresas (CRUD)
class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'