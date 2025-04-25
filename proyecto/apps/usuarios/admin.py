# backend/proyecto/apps/usuarios/admin.py
from django.contrib import admin
# NO importamos UserAdmin aquí
# NO importamos UserCreationForm/UserChangeForm de auth aquí
from django import forms
from .models import Usuario, Rol, Empresa
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password # Para hashear

# --- Formulario para CREAR usuarios (hereda de ModelForm) ---
class UsuarioCreationForm(forms.ModelForm): # <-- Hereda de forms.ModelForm
    # Añadimos los campos de contraseña manualmente
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), widget=forms.PasswordInput,
                                help_text=_("Enter the same password as before, for verification."))

    class Meta:
        model = Usuario
        # Incluye *todos* los campos que quieres en el formulario
        fields = ('cedula', 'email', 'username', 'nombre', 'apellido', 'rol', 'empresa')

    def clean_password2(self):
        # Validación manual de que las contraseñas coincidan
        cd = self.cleaned_data
        if 'password' in cd and 'password2' in cd:
            if cd['password'] != cd['password2']:
                raise forms.ValidationError(_('Las contraseñas no coinciden.'))
        # Siempre debes devolver el valor limpio del campo
        return cd.get('password2') # OJO: Devolvemos password2

    def clean_username(self):
        # Validación de unicidad de username si se proporciona
        username = self.cleaned_data.get("username")
        if username and Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya existe.")
        return username or None # Permite vacío

    def save(self, commit=True):
        # Hashea la contraseña ANTES de guardar el modelo
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        else:
            # Manejar caso sin contraseña si es necesario (aunque no debería pasar aquí)
            user.set_unusable_password() # O manejar de otra forma

        # Asigna username si está vacío
        if not user.username and user.email:
            user.username = user.email

        if commit:
            user.save()
        return user


# --- Formulario para EDITAR usuarios (hereda de ModelForm) ---
class UsuarioChangeForm(forms.ModelForm): # <-- Hereda de forms.ModelForm
    class Meta:
        model = Usuario
        # Campos para editar (sin password aquí, se maneja diferente)
        fields = ('cedula', 'username', 'email', 'nombre', 'apellido', 'rol', 'empresa',
                  'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')


# --- Admin Config - HEREDANDO SOLO DE ModelAdmin ---
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin): # <-- Hereda de ModelAdmin
    # Formularios a usar
    form = UsuarioChangeForm        # Formulario de edición
    add_form = UsuarioCreationForm  # Formulario de creación

    # Display y búsqueda
    list_display = ('cedula', 'email', 'username', 'nombre', 'apellido', 'rol', 'empresa', 'is_staff')
    search_fields = ('cedula', 'email', 'username', 'nombre', 'apellido' 'empresa__nombre',)
    ordering = ('cedula',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'rol', 'empresa')

    # Fieldsets para EDITAR (MANUAL)
    # Quitamos 'password' de aquí. El cambio de contraseña se hace desde la vista de usuario.
    fieldsets = (
        (None, {'fields': ('cedula',)}),
        (_('Información Personal'), {'fields': ('nombre', 'apellido', 'email', 'username', 'rol', 'empresa')}),
        (_('Permisos'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    # Fieldsets para CREAR (MANUAL, incluyendo passwords)
    add_fieldsets = (
        (None, {
            'fields': ('cedula', 'password', 'password2', 'email', 'username', 'nombre', 'apellido', 'rol', 'empresa'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions',)

    # Sobrescribimos get_fieldsets para usar add_fieldsets al crear
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    # Sobrescribimos get_form para usar el formulario correcto
    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        else:
            defaults['form'] = self.form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    # IMPORTANTE: save_model ahora DEBE hashear la contraseña porque ModelAdmin no lo hace
    def save_model(self, request, obj, form, change):
        """Hashea la contraseña al crear."""
        if not change: # Solo al crear
            password = form.cleaned_data.get("password")
            if password:
                obj.set_password(password)
            else:
                obj.set_unusable_password() # Marcar si no se dio contraseña

        # Lógica para asignar username si está vacío (del modelo)
        if not obj.username and obj.email:
            obj.username = obj.email

        super().save_model(request, obj, form, change)

# --- Rol Admin ---
@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'telefono')
    search_fields = ('nombre', 'nit')