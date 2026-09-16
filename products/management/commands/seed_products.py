import os
import json
from django.core.management.base import BaseCommand
from catalog.models import Category
from products.models import Product

class Command(BaseCommand):
    help = "Seed authentic real-life products into PostgreSQL database"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding authentic products from fixtures/products_mock.json..."))

        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "fixtures",
            "products_mock.json"
        )

        if not os.path.exists(fixture_path):
            self.stdout.write(self.style.ERROR(f"Fixture file not found at {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            products_list = json.load(f)

        count = 0
        for item in products_list:
            cat_slug = item.get("category_slug")
            category = None
            try:
                category = Category.objects.get(slug=cat_slug)
            except Category.DoesNotExist:
                # Try finding by partial slug match
                category = Category.objects.filter(slug__icontains=cat_slug).first()
                if not category:
                    category = Category.objects.filter(is_active=True).first()

            if not category:
                self.stdout.write(self.style.ERROR(f"No category found for slug '{cat_slug}'"))
                continue

            product, created = Product.objects.get_or_create(
                name_en=item["name_en"],
                category=category,
                defaults={
                    "name_bn": item.get("name_bn"),
                    "brand": item.get("brand", "MetroBazar Select"),
                    "unit": item.get("unit", "1 pc"),
                    "base_price": item.get("base_price", 100.00),
                    "description": item.get("description", ""),
                    "is_active": True,
                }
            )

            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created Product: {product.name_en} under '{category.name_en}'"))
            else:
                product.base_price = item.get("base_price", product.base_price)
                product.brand = item.get("brand", product.brand)
                product.unit = item.get("unit", product.unit)
                product.save()
                self.stdout.write(self.style.NOTICE(f"  Updated Product: {product.name_en}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {count} mock products into PostgreSQL database!"))
