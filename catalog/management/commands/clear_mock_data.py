from django.core.management.base import BaseCommand
from django.core.cache import cache
from catalog.models import Category
from products.models import Product
from orders.models import Order
from cart.models import GuestCart

class Command(BaseCommand):
    help = "Purge all mock data (categories, products, orders, guest carts) from database and clear Redis cache"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting mock data purge from PostgreSQL database..."))

        # 1. Delete Orders
        orders_deleted, _ = Order.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"  Deleted {orders_deleted} order records."))

        # 2. Delete Guest Carts
        carts_deleted, _ = GuestCart.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"  Deleted {carts_deleted} guest cart records."))

        # 3. Delete Products
        prods_deleted, _ = Product.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"  Deleted {prods_deleted} product records."))

        # 4. Delete Categories
        cats_deleted, _ = Category.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"  Deleted {cats_deleted} category records."))

        # 5. Flush Redis Cache
        cache.clear()
        self.stdout.write(self.style.SUCCESS("  Flushed Redis cache."))

        self.stdout.write(self.style.SUCCESS("All mock data wiped successfully! Database is clean."))
