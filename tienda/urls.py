from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Panel de administración Django (superusuarios)
    path('admin-django/', admin.site.urls),  # Cambiado para evitar conflicto con /admin/
    
    # URLs de la app carrito CON namespace
    path('', include('carrito.urls', namespace='carrito')),
    
    # URLs de autenticación globales (sin namespace)
    path('login/', 
        auth_views.LoginView.as_view(
            template_name='carrito/login.html',
            redirect_authenticated_user=True
        ), 
        name='login'),
    
    path('logout/', 
        auth_views.LogoutView.as_view(
            next_page='carrito:lista_productos'
        ), 
        name='logout'),
]

# Configuración para archivos media y estáticos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)