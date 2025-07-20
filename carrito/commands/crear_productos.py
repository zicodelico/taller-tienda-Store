from django.core.management.base import BaseCommand
from carrito.models import Producto

class Command(BaseCommand):
    help = 'Crea productos ficticios para pruebas'

    def handle(self, *args, **options):
        productos = [
            {"nombre": "Smartphone X", "descripcion": "Último modelo", "precio": 899.99, "inventario": 50},
            {"nombre": "Laptop Pro", "descripcion": "16GB RAM", "precio": 1299.99, "inventario": 30},
            {"nombre": "Auriculares", "descripcion": "Cancelación de ruido", "precio": 199.99, "inventario": 100},
            {"nombre": "Smart TV 55\"", "descripcion": "4K HDR", "precio": 599.99, "inventario": 20},
            {"nombre": "Tablet 10\"", "descripcion": "128GB", "precio": 349.99, "inventario": 40}
        ]

        for p in productos:
            Producto.objects.create(**p)
            self.stdout.write(self.style.SUCCESS(f'Producto creado: {p["nombre"]}'))