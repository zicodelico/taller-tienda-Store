from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_POST
from django.db import models
from .models import Producto, Carrito, ItemCarrito
from .forms import RegistroForm, LoginForm, ProductoForm


# -------------------------------
# Funciones auxiliares
# -------------------------------

def obtener_o_crear_carrito(user):
    """Obtiene el carrito existente o crea uno nuevo para el usuario"""
    try:
        return user.carrito
    except ObjectDoesNotExist:
        return Carrito.objects.create(usuario=user)

def es_administrador(user):
    """Verifica si el usuario es administrador (staff o superuser)"""
    return user.is_active and (user.is_superuser or user.is_staff)

# -------------------------------
# Vistas públicas
# -------------------------------

def lista_productos(request):
    """Muestra todos los productos disponibles"""
    productos = Producto.objects.filter(inventario__gt=0)
    carrito_items_count = 0
    
    if request.user.is_authenticated:
        carrito = obtener_o_crear_carrito(request.user)
        carrito_items_count = carrito.cantidad_items()
    
    return render(request, 'carrito/lista_productos.html', {
        'productos': productos,
        'carrito_items_count': carrito_items_count
    })

@login_required
def detalle_producto(request, producto_id):
    """Muestra los detalles de un producto específico"""
    producto = get_object_or_404(Producto, id=producto_id)
    carrito = obtener_o_crear_carrito(request.user)
    en_carrito = carrito.items.filter(producto=producto).exists()
    
    return render(request, 'carrito/detalle_producto.html', {
        'producto': producto,
        'en_carrito': en_carrito,
        'tiene_imagen': producto.imagen and hasattr(producto.imagen, 'url')
    })

@login_required
def ver_carrito(request):
    """Muestra el contenido del carrito"""
    carrito = obtener_o_crear_carrito(request.user)
    return render(request, 'carrito/carrito.html', {
        'carrito': carrito,
        'items': carrito.items.select_related('producto'),
        'total': carrito.total()
    })

@login_required
def agregar_al_carrito(request, producto_id):
    """Agrega un producto al carrito con validación de stock"""
    producto = get_object_or_404(Producto, id=producto_id)
    cantidad = int(request.POST.get('cantidad', 1))
    carrito = obtener_o_crear_carrito(request.user)
    
    try:
        # Validación de stock disponible
        if cantidad > producto.inventario:
            messages.warning(request, f"No hay suficiente stock de {producto.nombre}")
            return redirect(request.META.get('HTTP_REFERER', 'carrito:lista_productos'))
        
        # Agregar al carrito
        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            defaults={'cantidad': cantidad}
        )
        
        if not created:
            if (item.cantidad + cantidad) > producto.inventario:
                messages.warning(request, f"No puedes agregar más de {producto.inventario} unidades")
            else:
                item.cantidad += cantidad
                item.save()
                messages.success(request, f"Se agregaron {cantidad} {producto.nombre} al carrito")
        else:
            messages.success(request, f"{producto.nombre} agregado al carrito")
            
    except Exception as e:
        messages.error(request, f"Error al agregar producto: {str(e)}")
    
    return redirect(request.META.get('HTTP_REFERER', 'carrito:lista_productos'))

@login_required
def actualizar_carrito(request, item_id):
    """Actualiza la cantidad de un item en el carrito"""
    carrito = obtener_o_crear_carrito(request.user)
    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)
    nueva_cantidad = int(request.POST.get('cantidad', 1))
    
    try:
        if nueva_cantidad <= 0:
            carrito.remover_producto(item.producto)
            messages.success(request, f"{item.producto.nombre} eliminado del carrito")
        else:
            # Validar que no exceda el inventario
            if nueva_cantidad > item.producto.inventario + item.cantidad:
                messages.error(request, f"No hay suficiente inventario. Máximo disponible: {item.producto.inventario}")
            else:
                diferencia = nueva_cantidad - item.cantidad
                carrito.agregar_producto(item.producto, diferencia)
                messages.success(request, f"Cantidad de {item.producto.nombre} actualizada")
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('carrito:ver_carrito')

@login_required
def eliminar_del_carrito(request, item_id):
    """Elimina un producto del carrito"""
    carrito = obtener_o_crear_carrito(request.user)
    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)
    nombre_producto = item.producto.nombre
    carrito.remover_producto(item.producto)
    messages.success(request, f"{nombre_producto} eliminado del carrito")
    return redirect('carrito:ver_carrito')

def registro(request):
    """Maneja el registro de nuevos usuarios con mejor manejo de errores"""
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                # Guardar el usuario
                user = form.save(commit=False)
                user.email = form.cleaned_data.get('email')
                user.save()
                
                # Crear carrito para el usuario
                Carrito.objects.create(usuario=user)
                
                # Autenticar y loguear al usuario
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password1')
                user = authenticate(username=username, password=password)
                
                if user is not None:
                    login(request, user)
                    messages.success(request, "Registro exitoso. ¡Bienvenido!")
                    return redirect('carrito:lista_productos')
                else:
                    messages.error(request, "Error al autenticar al usuario después del registro")
            except Exception as e:
                messages.error(request, f"Error al registrar usuario: {str(e)}")
        else:
            # Mostrar errores específicos del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegistroForm()
    
    return render(request, 'carrito/registro.html', {'form': form})

def login_view(request):
    """Maneja el inicio de sesión con mejor feedback"""
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                obtener_o_crear_carrito(user)
                messages.success(request, f"Bienvenido de nuevo, {username}!")
                return redirect('carrito:lista_productos')
            else:
                messages.error(request, "Usuario o contraseña incorrectos")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario")
    else:
        form = LoginForm()
    
    return render(request, 'carrito/login.html', {'form': form})

@login_required
def checkout(request):
    """Procesa la compra"""
    carrito = obtener_o_crear_carrito(request.user)
    
    if carrito.items.count() == 0:
        messages.warning(request, "Tu carrito está vacío")
        return redirect('carrito:ver_carrito')
    
    if request.method == 'POST':
        try:
            # Verificar stock antes de procesar
            for item in carrito.items.all():
                if item.cantidad > item.producto.inventario:
                    messages.error(request, f"No hay suficiente stock de {item.producto.nombre}")
                    return redirect('carrito:ver_carrito')
            
            # Procesar compra (simulado)
            carrito.limpiar()
            messages.success(request, "¡Compra realizada con éxito!")
            return render(request, 'carrito/orden_completada.html')
        
        except Exception as e:
            messages.error(request, f"Error al procesar la compra: {str(e)}")
            return redirect('carrito:ver_carrito')
    
    return render(request, 'carrito/checkout.html', {
        'carrito': carrito,
        'items': carrito.items.select_related('producto'),
        'total': carrito.total()
    })

@login_required
def limpiar_carrito(request):
    """Vacia completamente el carrito de compras"""
    carrito = obtener_o_crear_carrito(request.user)
    carrito.limpiar()
    messages.success(request, "Carrito vaciado correctamente")
    return redirect('carrito:ver_carrito')

# -------------------------------
# Vistas de administración 
# -------------------------------

@staff_member_required
def panel_administracion(request):
    """Panel principal de administración"""
    total_productos = Producto.objects.count()
    productos_bajo_stock = Producto.objects.filter(inventario__lt=5).order_by('inventario')
    total_usuarios = User.objects.count()  # Nuevo: conteo de usuarios
    
    return render(request, 'carrito/admin/panel.html', {
        'total_productos': total_productos,
        'productos_bajo_stock': productos_bajo_stock,
        'ultimos_productos': Producto.objects.order_by('-creado')[:5],
        'todos_los_productos': Producto.objects.all(),
        'total_usuarios': total_usuarios,  # Nuevo: pasar a template
        'productos_agotados': Producto.objects.filter(inventario=0)
    })

@staff_member_required
def admin_lista_productos(request):
    """Lista COMPLETA de productos para administradores"""
    busqueda = request.GET.get('q', '')
    productos = Producto.objects.all().order_by('-creado')
    
    if busqueda:
        productos = productos.filter(
            models.Q(nombre__icontains=busqueda) |
            models.Q(descripcion__icontains=busqueda)
        )
    
    # Agrupar por disponibilidad de stock
    productos_agotados = productos.filter(inventario=0)
    productos_bajo_stock = productos.filter(inventario__lt=5, inventario__gt=0)
    productos_disponibles = productos.filter(inventario__gte=5)
    
    return render(request, 'carrito/admin/lista_productos.html', {
        'productos_agotados': productos_agotados,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_disponibles': productos_disponibles,
        'busqueda': busqueda,
        'total_productos': productos.count()
    })

@staff_member_required
def crear_producto(request):
    """Creación de productos (versión mejorada)"""
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.creado_por = request.user
            
            # Validación adicional de precio
            if producto.precio <= 0:
                messages.error(request, "El precio debe ser mayor a cero")
                return render(request, 'carrito/admin/crear_producto.html', {'form': form})
            
            producto.save()
            
            messages.success(request, f"Producto '{producto.nombre}' creado exitosamente")
            return redirect('carrito:admin_lista_productos')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario")
    else:
        form = ProductoForm()
    
    return render(request, 'carrito/admin/crear_producto.html', {
        'form': form,
        'modo': 'crear'
    })

@staff_member_required
def editar_producto(request, producto_id):
    """Edición de productos sin restricciones"""
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f"Producto '{producto.nombre}' actualizado exitosamente")
            return redirect('carrito:admin_lista_productos')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario")
    else:
        form = ProductoForm(instance=producto)
    
    return render(request, 'carrito/admin/editar_producto.html', {
        'form': form,
        'producto': producto,
        'modo': 'editar'
    })

@staff_member_required
@require_POST
def eliminar_producto(request, producto_id):
    """Eliminación directa para administradores"""
    producto = get_object_or_404(Producto, id=producto_id)
    nombre_producto = producto.nombre
    
    try:
        # Verificar si el producto está en algún carrito
        en_carritos = ItemCarrito.objects.filter(producto=producto).exists()
        
        if en_carritos:
            messages.error(request, 
                f"No se puede eliminar '{nombre_producto}' porque está en carritos activos")
            return redirect('carrito:admin_lista_productos')
        
        producto.delete()
        messages.success(request, f"Producto '{nombre_producto}' eliminado permanentemente")
        
    except Exception as e:
        messages.error(request, f"Error al eliminar producto: {str(e)}")
    
    return redirect('carrito:admin_lista_productos')

@staff_member_required
def gestion_usuarios(request):
    """Vista completa de gestión de usuarios"""
    usuarios = User.objects.all().prefetch_related('groups')  # ✅ Corregido (usa prefetch_related)
    grupos = Group.objects.all()
    permisos = Permission.objects.all()
    
    return render(request, 'carrito/admin/gestion_usuarios.html', {
        'usuarios': usuarios,
        'grupos': grupos,
        'permisos': permisos,
        'content_types': ContentType.objects.all()
    })

@staff_member_required
@require_POST
def actualizar_usuario(request, user_id):
    """Actualiza permisos y grupos de usuario"""
    usuario = get_object_or_404(User, id=user_id)
    
    if request.user.is_superuser:  # Solo superusuarios pueden hacer esto
        # Manejar grupos
        grupos_seleccionados = request.POST.getlist('grupos')
        usuario.groups.set(grupos_seleccionados)
        
        # Manejar permisos individuales
        permisos_seleccionados = request.POST.getlist('permisos')
        usuario.user_permissions.set(permisos_seleccionados)
        
        # Actualizar estado de staff/superuser
        usuario.is_staff = 'is_staff' in request.POST
        usuario.is_superuser = 'is_superuser' in request.POST
        usuario.save()
        
        messages.success(request, f"Usuario {usuario.username} actualizado")
    else:
        messages.error(request, "No tienes permisos para esta acción")
    
    return redirect('carrito:gestion_usuarios')

@staff_member_required
def reportes_productos(request):
    """Reportes avanzados con gráficos y estadísticas"""
    from django.db.models import Sum, Avg, Count
    import datetime
    
    # Estadísticas básicas
    estadisticas = {
        'total_inventario': Producto.objects.aggregate(Sum('inventario'))['inventario__sum'],
        'valor_total': Producto.objects.aggregate(
            total=Sum(models.F('inventario') * models.F('precio'))
        )['total'] or 0,
        'precio_promedio': Producto.objects.aggregate(Avg('precio'))['precio__avg'],
        'productos_sin_imagen': Producto.objects.filter(imagen__isnull=True).count()
    }
    
    # Productos más populares (en carritos)
    productos_populares = ItemCarrito.objects.values(
        'producto__nombre'
    ).annotate(
        total_vendido=Sum('cantidad'),
        veces_agregado=Count('id')
    ).order_by('-total_vendido')[:10]
    
    # Evolución de inventario (últimos 30 días)
    fecha_limite = datetime.date.today() - datetime.timedelta(days=30)
    historial = Producto.objects.filter(
        actualizado__gte=fecha_limite
    ).order_by('actualizado').values(
        'actualizado'
    ).annotate(
        total=Count('id'),
        nuevo_inventario=Sum('inventario')
    )
    
    return render(request, 'carrito/admin/reportes.html', {
        'estadisticas': estadisticas,
        'productos_populares': productos_populares,
        'historial': historial,
        'hoy': datetime.date.today()
    })