from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _

class Empresa(models.Model):
    nombre = models.CharField(max_length=255, unique=True, verbose_name=_("Nombre de la Empresa"))
    nit = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name=_("NIT"))
    direccion = models.CharField(max_length=255, blank=True, verbose_name=_("Dirección"))
    telefono = models.CharField(max_length=50, blank=True, verbose_name=_("Teléfono"))
    # Puedes añadir más campos si son necesarios

    class Meta:
        verbose_name = _("Empresa")
        verbose_name_plural = _("Empresas")

    def __str__(self):
        return self.nombre

class UsuarioManager(BaseUserManager):
    def create_user(self, cedula, password=None, **extra_fields):
        """Crea y guarda un Usuario con la cédula y contraseña."""
        if not cedula:
            raise ValueError(_('La cédula es obligatoria'))
        user = self.model(cedula=cedula, **extra_fields)
        if password:
            user.set_password(password)  # Usar set_password SIEMPRE
        else:
            user.password = None

        user.save(using=self._db)
        return user

    def create_superuser(self, cedula, password, **extra_fields):
        """Crea y guarda un superusuario con cédula y contraseña."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('email', 'admin@example.com')  # Pon un valor por defecto
       # extra_fields.setdefault('username', 'admin')  # Pon un valor por defecto

        try:
            rol_admin = Rol.objects.get(nombre='admin')
        except Rol.DoesNotExist:
            raise ValueError("El rol 'admin' debe existir para crear un superusuario.")
        extra_fields.setdefault('rol', rol_admin)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('El superusuario debe tener is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('El superusuario debe tener is_superuser=True.'))

        return self.create_user(cedula, password, **extra_fields)



class Rol(models.Model):
    ROL_CHOICES = (
        ('conductor', 'Conductor'),
        ('cliente', 'Cliente'),
        ('jefe_inventario', 'Jefe de Inventario'),
        ('jefe_empresa', 'Jefe de Empresa'),
        ('admin', 'Admin'),
    )
    nombre = models.CharField(max_length=20, choices=ROL_CHOICES, unique=True)

    def __str__(self):
        return self.nombre

class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, blank=True, null=True) #Opcional
    username = models.CharField(max_length=150, unique=True, blank=True, null=True) #Opcional, pero único si se proporciona
    nombre = models.CharField(max_length=255, blank=True)
    apellido = models.CharField(max_length=255, blank=True)
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    cedula = models.CharField(max_length=20, unique=True, null=True, blank=True)  # ¡Cédula!
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL, # Si se borra la empresa, no borrar al usuario, solo quitar la relación
        null=True,
        blank=True, # Permitir usuarios sin empresa (ej. admin, conductor)
        related_name='empleados',
        verbose_name=_("Empresa")
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'cedula'  # ¡Cédula como identificador!
    REQUIRED_FIELDS = []       # Cedula ya es el USERNAME_FIELD, así que no necesita estar aquí


    def __str__(self):
        return self.cedula if self.cedula else str(self.email)  # Asegura que siempre retorne un string

    def save(self, *args, **kwargs):
        if self.rol and self.rol.nombre in ['conductor', 'cliente'] and not self.cedula:
            raise ValueError("Los conductores y clientes deben tener una cédula.")
        if not self.username and self.email:  # Solo asignar si hay un email
            self.username = self.email
        super().save(*args, **kwargs)
