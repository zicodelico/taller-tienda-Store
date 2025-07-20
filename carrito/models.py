from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class Producto(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del producto")
    descripcion = models.TextField(verbose_name="Descripción")
    precio = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Precio unitario"
    )
    inventario = models.PositiveIntegerField(
        default=0,
        verbose_name="Cantidad en inventario"
    )
    imagen = models.ImageField(
        upload_to='productos/', 
        null=True, 
        blank=True,
        verbose_name="Imagen del producto"
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        verbose_name="Creado por"
    )
    
    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-creado']
        permissions = [
            ("puede_ver_productos", "Puede ver listado de productos"),
            ("puede_editar_producto", "Puede editar cualquier producto"),
            ("puede_eliminar_producto", "Puede eliminar productos"),
            ("puede_crear_producto", "Puede crear nuevos productos"),
            ("puede_gestionar_inventario", "Puede actualizar inventarios"),
            ("puede_ver_reportes", "Puede acceder a reportes"),
        ]
    
    def __str__(self):
        return f"{self.nombre} (${self.precio})"
    
    def disminuir_inventario(self, cantidad):
        """Reduce el inventario y guarda el producto"""
        if cantidad > self.inventario:
            raise ValueError("No hay suficiente inventario")
        self.inventario -= cantidad
        self.save()
    
    def aumentar_inventario(self, cantidad):
        """Aumenta el inventario y guarda el producto"""
        self.inventario += cantidad
        self.save()

    @property
    def estado_stock(self):
        """Devuelve el estado del stock como texto"""
        if self.inventario == 0:
            return "Agotado"
        elif self.inventario < 5:
            return "Bajo stock"
        return "Disponible"

class Carrito(models.Model):
    usuario = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='carrito'
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Carrito de compras"
        verbose_name_plural = "Carritos de compras"
        permissions = [
            ("puede_ver_carritos", "Puede ver todos los carritos"),
            ("puede_limpiar_carritos", "Puede limpiar carritos ajenos"),
        ]
    
    def __str__(self):
        return f"Carrito de {self.usuario.username} (ID: {self.id})"
    
    def total(self):
        """Calcula el total del carrito"""
        return sum(item.subtotal() for item in self.items.all())
    
    def cantidad_items(self):
        """Devuelve la cantidad total de items en el carrito"""
        return sum(item.cantidad for item in self.items.all())
    
    def agregar_producto(self, producto, cantidad=1):
        """Agrega un producto al carrito con la cantidad especificada"""
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        
        if cantidad > producto.inventario:
            raise ValueError(f"No hay suficiente inventario. Disponible: {producto.inventario}")
        
        item, created = ItemCarrito.objects.get_or_create(
            carrito=self,
            producto=producto,
            defaults={'cantidad': cantidad}
        )
        
        if not created:
            item.cantidad += cantidad
            item.save()
        
        producto.disminuir_inventario(cantidad)
        self.save()
    
    def remover_producto(self, producto, cantidad=None):
        """Elimina un producto del carrito o reduce su cantidad"""
        try:
            item = self.items.get(producto=producto)
            if cantidad is None or cantidad >= item.cantidad:
                producto.aumentar_inventario(item.cantidad)
                item.delete()
            else:
                producto.aumentar_inventario(cantidad)
                item.cantidad -= cantidad
                if item.cantidad <= 0:
                    item.delete()
                else:
                    item.save()
            self.save()
        except ItemCarrito.DoesNotExist:
            pass
    
    def limpiar(self):
        """Vacía completamente el carrito y devuelve los productos al inventario"""
        for item in self.items.all():
            item.producto.aumentar_inventario(item.cantidad)
            item.delete()
        self.save()

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name='items'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='carrito_items'
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    agregado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Ítem del carrito"
        verbose_name_plural = "Ítems del carrito"
        unique_together = ['carrito', 'producto']
        ordering = ['-agregado']
        permissions = [
            ("puede_ver_items", "Puede ver todos los ítems"),
            ("puede_modificar_items", "Puede modificar ítems ajenos"),
        ]
    
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en carrito {self.carrito.id}"
    
    def subtotal(self):
        """Calcula el subtotal para este item"""
        return self.producto.precio * self.cantidad
    
    def save(self, *args, **kwargs):
        """Valida la cantidad antes de guardar"""
        inventario_disponible = self.producto.inventario
        if self.pk:  # Si ya existe el item
            item_original = ItemCarrito.objects.get(pk=self.pk)
            inventario_disponible += item_original.cantidad
        
        if self.cantidad > inventario_disponible:
            raise ValueError(f"No hay suficiente inventario. Máximo disponible: {inventario_disponible}")
        
        super().save(*args, **kwargs)