from django.urls import path
from . import views
from django.views.decorators.http import require_POST

app_name = 'carrito'  # Namespace para todas las URLs

urlpatterns = [
    # --------------------------------------------
    # Páginas públicas
    # --------------------------------------------
    path('', views.lista_productos, name='lista_productos'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    
    # --------------------------------------------
    # Gestión del carrito
    # --------------------------------------------
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('actualizar/<int:item_id>/', views.actualizar_carrito, name='actualizar_carrito'),
    path('eliminar/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/limpiar/', views.limpiar_carrito, name='limpiar_carrito'),
    
    # --------------------------------------------
    # Proceso de compra
    # --------------------------------------------
    path('checkout/', views.checkout, name='checkout'),
    
    # --------------------------------------------
    # Autenticación
    # --------------------------------------------
    path('registro/', views.registro, name='registro'),
    
    # --------------------------------------------
    # Administración (Protegidas con decoradores)
    # --------------------------------------------
    path('admin/', views.panel_administracion, name='admin_panel'),
    path('admin/productos/', views.admin_lista_productos, name='admin_lista_productos'),
    path('admin/productos/nuevo/', views.crear_producto, name='admin_crear_producto'),
    path('admin/productos/editar/<int:producto_id>/', views.editar_producto, name='admin_editar_producto'),
    path('admin/productos/eliminar/<int:producto_id>/', 
         require_POST(views.eliminar_producto),  # Solo acepta POST
         name='admin_eliminar_producto'),
    path('admin/reportes/', views.reportes_productos, name='admin_reportes'),
    
    # ============================================
    # NUEVAS URLs PARA GESTIÓN DE USUARIOS
    # ============================================
    path('admin/usuarios/', views.gestion_usuarios, name='gestion_usuarios'),
    path('admin/usuarios/actualizar/<int:user_id>/', 
         require_POST(views.actualizar_usuario),  # Solo acepta POST
         name='actualizar_usuario'),
]
