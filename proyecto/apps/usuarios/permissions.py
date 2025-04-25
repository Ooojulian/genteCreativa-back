from rest_framework import permissions
import logging # Opcional
logger = logging.getLogger(__name__) # Opcional

class IsOwner(permissions.BasePermission):
    """
    Permiso personalizado para permitir solo a los propietarios de un objeto editarlo.
    """
    message = "No tienes permiso para acceder a este objeto, no eres el propietario." #Mensaje de error
    def has_object_permission(self, request, view, obj):
        # La propiedad 'user' se establece automáticamente en las vistas de DRF
        return obj == request.user

class IsJefeInventario(permissions.BasePermission):
    message = "Se requiere rol de Jefe de Inventario."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol and request.user.rol.nombre == 'jefe_inventario'
        

class IsConductor(permissions.BasePermission):
    message = "No tienes permiso para acceder a esta vista, no eres un conductor."

    def has_permission(self, request, view):
        # Verifica si el usuario está autenticado.
        if not request.user.is_authenticated:
            return False  # Si no está autenticado, no hay permiso

        # Verifica si el usuario tiene un rol asignado *antes* de acceder a .nombre
        if request.user.rol is None:
            return False  # Si no tiene rol, no es conductor

        return request.user.rol.nombre == 'conductor'


class IsCliente(permissions.BasePermission):
    """
    Permite el acceso solo a usuarios autenticados que tienen el rol de 'cliente'.
    """
    message = "No tienes permiso para realizar esta acción, se requiere rol de cliente."

    def has_permission(self, request, view):
        # Verifica que el usuario esté autenticado y que tenga el atributo 'rol'
        # y que el nombre de ese rol sea 'cliente'
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'rol') and
            request.user.rol is not None and
            getattr(request.user.rol, 'nombre', None) == 'cliente'
        )
    
class IsJefeEmpresa(permissions.BasePermission):
    """
    Permiso para permitir acceso solo a usuarios con rol 'jefe_empresa'.
    """
    message = "No tienes permiso para realizar esta acción, se requiere rol de Jefe de Empresa."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol and request.user.rol.nombre == 'jefe_empresa'
# 