import os
import json
from django.core.management.base import BaseCommand
from django.core.cache import cache
from catalog.models import Category
from catalog.cache import CATEGORY_LIST_CACHE_KEY

class Command(BaseCommand):
    help = "Seed authentic real-life categories from fixtures/categories_mock.json into PostgreSQL database"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding authentic categories from fixtures/categories_mock.json..."))

        # 1. Ensure Root Category 'Food' exists
        food_root, created = Category.objects.get_or_create(
            slug="food",
            defaults={
                "name_en": "Food",
                "name_bn": "খাদ্যসামগ্রী",
                "parent": None,
                "display_order": 1,
                "is_active": True,
                "is_featured": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created Root Category: {food_root.name_en}"))
        else:
            self.stdout.write(self.style.NOTICE(f"Found Root Category: {food_root.name_en} (ID: {food_root.id})"))

        # 2. Load mock data from fixtures folder
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "fixtures",
            "categories_mock.json"
        )

        if not os.path.exists(fixture_path):
            self.stdout.write(self.style.ERROR(f"Fixture file not found at {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            categories_tree = json.load(f)

        for cat_item in categories_tree:
            children = cat_item.pop("children", [])
            cat_obj, c_created = Category.objects.get_or_create(
                slug=cat_item["slug"],
                defaults={
                    "name_en": cat_item["name_en"],
                    "name_bn": cat_item.get("name_bn"),
                    "parent": food_root,
                    "display_order": cat_item.get("display_order", 0),
                    "is_active": True,
                    "is_featured": cat_item.get("is_featured", True),
                }
            )
            if not c_created:
                cat_obj.name_bn = cat_item.get("name_bn")
                cat_obj.parent = food_root
                cat_obj.save()
                self.stdout.write(self.style.NOTICE(f"  Updated Category: {cat_obj.name_en}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"  Created Category: {cat_obj.name_en}"))

            for order, sub_item in enumerate(children, start=1):
                sub_obj, sub_created = Category.objects.get_or_create(
                    slug=sub_item["slug"],
                    defaults={
                        "name_en": sub_item["name_en"],
                        "name_bn": sub_item.get("name_bn"),
                        "parent": cat_obj,
                        "display_order": order,
                        "is_active": True,
                        "is_featured": True,
                    }
                )
                if not sub_created:
                    sub_obj.name_bn = sub_item.get("name_bn")
                    sub_obj.parent = cat_obj
                    sub_obj.save()
                    self.stdout.write(self.style.NOTICE(f"    Updated Sub-category: {sub_obj.name_en}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"    Created Sub-category: {sub_obj.name_en}"))

        # Rebuild MPTT tree and clear Redis cache
        Category.objects.rebuild()
        cache.delete(CATEGORY_LIST_CACHE_KEY)
        self.stdout.write(self.style.SUCCESS("Successfully seeded categories from fixtures/categories_mock.json into PostgreSQL database!"))
