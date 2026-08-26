from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from .models import Category
from .serializers import CategoryTreeSerializer


class CategorySerializerTests(SimpleTestCase):
    """
    Unit tests for category serializer.
    """

    def test_category_tree_serializer(self):
        # Create root categories
        cat1 = Category.objects.create(
            name_en="Electronics",
            name_bn="ইলেক্ট্রনিক্স",
            slug="electronics",
            is_active=True,
            display_order=1,
        )

        cat2 = Category.objects.create(
            name_en="Clothing",
            name_bn="পোশাক",
            slug="clothing",
            is_active=True,
            display_order=2,
        )

        # Create sub-categories
        cat1_1 = Category.objects.create(
            name_en="Mobiles",
            name_bn="মোবাইলস",
            slug="mobiles",
            parent=cat1,
            is_active=True,
            display_order=1,
        )

        Category.objects.create(
            name_en="Inactive Mobile",
            name_bn="নিষ্ক্রিয় মোবাইল",
            slug="inactive-mobile",
            parent=cat1,
            is_active=False,
            display_order=2,
        )

        cat2_1 = Category.objects.create(
            name_en="Men's Clothing",
            name_bn="পুরুষদের পোশাক",
            slug="mens-clothing",
            parent=cat2,
            is_active=True,
            display_order=1,
        )

        # Create nested sub-category
        cat2_1_1 = Category.objects.create(
            name_en="Shirts",
            name_bn="শার্ট",
            slug="shirts",
            parent=cat2_1,
            is_active=True,
            display_order=1,
        )

        factory = APIRequestFactory()
        request = factory.get("/")

        serializer = CategoryTreeSerializer(
            Category.objects.filter(
                parent=None,
                is_active=True,
            ),
            many=True,
            context={"request": request},
        )

        data = serializer.data

        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

        # Test root category Electronics
        electronics = next(
            c for c in data if c["slug"] == "electronics"
        )
        self.assertEqual(electronics["name_en"], "Electronics")
        self.assertIsInstance(electronics["children"], list)
        self.assertEqual(len(electronics["children"]), 1)

        # Test sub-category Mobiles
        mobiles = electronics["children"][0]
        self.assertEqual(mobiles["slug"], "mobiles")
        self.assertEqual(mobiles["name_bn"], "মোবাইলস")
        self.assertEqual(mobiles["children"], [])  # No children

        # Test root category Clothing
        clothing = next(
            c for c in data if c["slug"] == "clothing"
        )
        self.assertEqual(clothing["name_en"], "Clothing")
        self.assertIsInstance(clothing["children"], list)
        self.assertEqual(len(clothing["children"]), 1)

        # Test Men's Clothing
        mens_clothing = clothing["children"][0]
        self.assertEqual(mens_clothing["slug"], "mens-clothing")
        self.assertEqual(len(mens_clothing["children"]), 1)

        # Test nested Shirts
        shirts = mens_clothing["children"][0]
        self.assertEqual(shirts["slug"], "shirts")
        self.assertEqual(shirts["children"], [])

        # Test that inactive category is NOT returned
        self.assertNotIn(
            "inactive-mobile",
            [c["slug"] for c in electronics["children"]],
        )


class CategoryViewTests(SimpleTestCase):
    """
    Tests for category API views.
    """

    def setUp(self):
        # Create categories
        self.cat1 = Category.objects.create(
            name_en="Electronics",
            name_bn="ইলেক্ট্রনিক্স",
            slug="electronics",
            is_active=True,
            display_order=1,
        )

        self.cat2 = Category.objects.create(
            name_en="Clothing",
            name_bn="পোশাক",
            slug="clothing",
            is_active=True,
            display_order=2,
        )

        Category.objects.create(
            name_en="Inactive",
            name_bn="নিষ্ক্রিয়",
            slug="inactive",
            is_active=False,
            display_order=3,
        )

        Category.objects.create(
            name_en="Out Of Order",
            name_bn="অকেজো",
            slug="out-of-order",
            parent=self.cat1,
            is_active=False,
        )

    def test_category_list_view(self):
        from config.catalog.views import (
            CACHE_TTL,
        )
        from unittest.mock import patch

        url = reverse("category-list")

        # Test unauthenticated access
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.data

        # Should only return active root categories
        self.assertEqual(
            len(data),
            2,
        )
        self.assertTrue(
            all(
                item["is_active"]
                for item in data
            )
        )

        # Check fields returned
        first = data[0]
        self.assertIn("id", first)
        self.assertIn("name_en", first)
        self.assertIn("name_bn", first)
        self.assertIn("slug", first)
        self.assertIn("icon", first)
        self.assertIn("banner", first)
        self.assertIn("display_order", first)
        self.assertIn("children", first)

        # Test caching
        with patch("django.core.cache.cache.get") as mock_get:
            with patch("django.core.cache.cache.set") as mock_set:
                self.client.get(url)

                mock_get.assert_called_once()
                mock_set.assert_called_once()

                # Should use correct cache key
                args, _ = mock_get.call_args
                self.assertTrue(
                    args[0].startswith("category_detail_")
                )

    def test_category_detail_view(self):
        from unittest.mock import patch

        url = reverse("category-detail", kwargs={
            "slug": self.cat1.slug
        })

        # Test normal flow
        with patch("django.core.cache.cache.get") as mock_get:
            with patch("django.core.cache.cache.set") as mock_set:
                response = self.client.get(url)

                mock_get.assert_called_once()
                mock_set.assert_called_once()

                self.assertEqual(
                    response.status_code,
                    200,
                )

                data = response.data
                self.assertIsInstance(data, dict)
                self.assertEqual(
                    data["slug"],
                    "electronics",
                )
                self.assertIn("children", data)

                # Test cache hit
                mock_get.reset_mock()
                mock_set.reset_mock()

                response_cached = self.client.get(url)
                mock_get.assert_
