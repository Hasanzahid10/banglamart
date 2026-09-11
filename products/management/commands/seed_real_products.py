import uuid
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from catalog.models import Category
from products.models import Product, ProductInventory
from logistics.models import DarkStore, ServiceArea


class Command(BaseCommand):
    help = "Purge old mock products and seed comprehensive realistic products across ALL categories and subcategories."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Purging invalid test categories & old mock products..."))

        # Clean up test categories if present
        Category.objects.filter(name_en__in=["aaa", "bbbb", "ccccc"]).delete()
        Category.objects.filter(slug__in=["aaa", "bbbb", "ccccc"]).delete()

        # Clear old products & inventory
        ProductInventory.objects.all().delete()
        Product.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Existing products & test categories cleared."))

        # 1. Ensure ServiceArea & DarkStore exist
        service_area, _ = ServiceArea.objects.get_or_create(
            name="Dhaka Central",
            defaults={"code": "DHK-CENTRAL", "is_active": True}
        )

        dark_store, _ = DarkStore.objects.get_or_create(
            code="DHK-DS-001",
            defaults={
                "name": "Dhaka Central Dark Store",
                "service_area": service_area,
                "address": "Banani, Dhaka",
                "contact_number": "01700000000",
                "is_active": True,
            }
        )

        # 2. Comprehensive Dataset for ALL Categories & Subcategories
        PRODUCTS_DATA = [
            # =========================================================
            # GROCERY & COOKING / COOKING
            # =========================================================
            # Rice & Grains / Rice & Lentils
            {
                "cat_names": ["Rice & Grains", "Rice & Lentils", "Rice & Pulses"],
                "parent_names": ["Grocery & Cooking", "Cooking", "Food"],
                "name_en": "Miniket Premium Rice 5kg",
                "name_bn": " মিনিকেট প্রিমিয়াম চাল ৫ কেজি",
                "brand": "Teer",
                "unit": "5 kg",
                "base_price": 385.00,
                "image": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=600&auto=format&fit=crop&q=80",
                "description": "Premium quality refined Miniket rice.",
            },
            {
                "cat_names": ["Rice & Grains", "Rice & Lentils", "Rice & Pulses"],
                "parent_names": ["Grocery & Cooking", "Cooking", "Food"],
                "name_en": "Nazirshail Special Rice 5kg",
                "name_bn": "নাজিরশাইল স্পেশাল চাল ৫ কেজি",
                "brand": "ACI Pure",
                "unit": "5 kg",
                "base_price": 420.00,
                "image": "https://images.unsplash.com/photo-1536304993881-ff6e9eefa2a6?w=600&auto=format&fit=crop&q=80",
                "description": "Long grain fragrant Nazirshail rice.",
            },
            {
                "cat_names": ["Rice & Grains", "Rice & Lentils", "Rice & Pulses"],
                "parent_names": ["Grocery & Cooking", "Cooking", "Food"],
                "name_en": "Kalijira Polao Rice 1kg",
                "name_bn": "কালিজিরা পোলাও চাল ১ কেজি",
                "brand": "Pran",
                "unit": "1 kg",
                "base_price": 160.00,
                "image": "https://images.unsplash.com/photo-1516684732162-798a0062be99?w=600&auto=format&fit=crop&q=80",
                "description": "Aromatic fine Kalijira rice for Polao & Biryani.",
            },

            # Dal & Pulses
            {
                "cat_names": ["Dal & Pulses", "Rice & Lentils", "Rice & Pulses"],
                "parent_names": ["Grocery & Cooking", "Cooking", "Food"],
                "name_en": "Deshi Red Lentils (Masoor Dal) 1kg",
                "name_bn": "দেশি মসুর ডাল ১ কেজি",
                "brand": "ACI Pure",
                "unit": "1 kg",
                "base_price": 140.00,
                "image": "https://images.unsplash.com/photo-1515543237350-b3eea1ec8082?w=600&auto=format&fit=crop&q=80",
                "description": "100% natural deshi red lentils.",
            },
            {
                "cat_names": ["Dal & Pulses", "Rice & Lentils", "Rice & Pulses"],
                "parent_names": ["Grocery & Cooking", "Cooking", "Food"],
                "name_en": "Mung Dal Special Cleaned 1kg",
                "name_bn": "মুগ ডাল স্পেশাল ১ কেজি",
                "brand": "Teer",
                "unit": "1 kg",
                "base_price": 175.00,
                "image": "https://images.unsplash.com/photo-1613758235256-42f2b38ef040?w=600&auto=format&fit=crop&q=80",
                "description": "Cleaned roasted yellow mung dal.",
            },

            # Edible Oil & Ghee / Oil & Ghee
            {
                "cat_names": ["Edible Oil & Ghee", "Oil & Ghee"],
                "parent_names": ["Grocery & Cooking", "Cooking"],
                "name_en": "Rupchanda Fortified Soyabean Oil 5L",
                "name_bn": "রূপচাঁদা সয়াবিন তেল ৫ লিটার",
                "brand": "Rupchanda",
                "unit": "5 L",
                "base_price": 835.00,
                "image": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=600&auto=format&fit=crop&q=80",
                "description": "Vitamin A fortified pure soyabean oil.",
            },
            {
                "cat_names": ["Edible Oil & Ghee", "Oil & Ghee"],
                "parent_names": ["Grocery & Cooking", "Cooking"],
                "name_en": "Radhuni Pure Mustard Oil 1L",
                "name_bn": "রাঁধুনী খাঁটি সরিষার তেল ১ লিটার",
                "brand": "Radhuni",
                "unit": "1 L",
                "base_price": 320.00,
                "image": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600&auto=format&fit=crop&q=80",
                "description": "Pungent cold pressed pure mustard oil.",
            },

            # Spices & Masala
            {
                "cat_names": ["Spices & Masala"],
                "parent_names": ["Grocery & Cooking"],
                "name_en": "Radhuni Turmeric Powder (Holud) 200g",
                "name_bn": "রাঁধুনী হলুদ গুঁড়া ২০০ গ্রাম",
                "brand": "Radhuni",
                "unit": "200 gm",
                "base_price": 85.00,
                "image": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=600&auto=format&fit=crop&q=80",
                "description": "Pure ground turmeric powder.",
            },
            {
                "cat_names": ["Spices & Masala"],
                "parent_names": ["Grocery & Cooking"],
                "name_en": "Radhuni Chilli Powder (Moriach) 200g",
                "name_bn": "রাঁধুনী মরিচ গুঁড়া ২০০ গ্রাম",
                "brand": "Radhuni",
                "unit": "200 gm",
                "base_price": 110.00,
                "image": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=600&auto=format&fit=crop&q=80",
                "description": "Hot red chilli powder.",
            },
            {
                "cat_names": ["Spices & Masala"],
                "parent_names": ["Grocery & Cooking"],
                "name_en": "Radhuni Beef Masala Pack 100g",
                "name_bn": "রাঁধুনী গরুর মাংসের মশলা ১০০ গ্রাম",
                "brand": "Radhuni",
                "unit": "100 gm",
                "base_price": 70.00,
                "image": "https://images.unsplash.com/photo-1509358271058-acd22cc93898?w=600&auto=format&fit=crop&q=80",
                "description": "Complete ready spice mix for delicious beef curry.",
            },

            # Salt & Sugar
            {
                "cat_names": ["Salt & Sugar"],
                "parent_names": ["Grocery & Cooking", "Cooking"],
                "name_en": "ACI Pure Salt Vacuum Evaporated 1kg",
                "name_bn": "এসিআই পিওর লবণ ১ কেজি",
                "brand": "ACI Pure",
                "unit": "1 kg",
                "base_price": 42.00,
                "image": "https://images.unsplash.com/photo-1518110168401-f287b3c60a28?w=600&auto=format&fit=crop&q=80",
                "description": "Iodized vacuum evaporated salt.",
            },
            {
                "cat_names": ["Salt & Sugar"],
                "parent_names": ["Grocery & Cooking", "Cooking"],
                "name_en": "Teer Pure White Refined Sugar 1kg",
                "name_bn": "তীর চিনি ১ কেজি",
                "brand": "Teer",
                "unit": "1 kg",
                "base_price": 140.00,
                "image": "https://images.unsplash.com/photo-1581441363689-1f3c3c414635?w=600&auto=format&fit=crop&q=80",
                "description": "Refined white crystal sugar.",
            },

            # Flour & Atta
            {
                "cat_names": ["Flour & Atta"],
                "parent_names": ["Grocery & Cooking"],
                "name_en": "Teer Whole Wheat Atta 2kg",
                "name_bn": "তীর আটা ২ কেজি",
                "brand": "Teer",
                "unit": "2 kg",
                "base_price": 130.00,
                "image": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&auto=format&fit=crop&q=80",
                "description": "Whole wheat flour for soft roti & paratha.",
            },

            # Sauces & Pickles
            {
                "cat_names": ["Sauces & Pickles"],
                "parent_names": ["Grocery & Cooking"],
                "name_en": "Pran Tomato Sauce Bottle 340g",
                "name_bn": "প্রাণ টমেটো সস ৩৪০ গ্রাম",
                "brand": "Pran",
                "unit": "340 gm",
                "base_price": 110.00,
                "image": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600&auto=format&fit=crop&q=80",
                "description": "Tangy tomato ketchup sauce.",
            },

            # =========================================================
            # FRUITS & VEGETABLES
            # =========================================================
            # Fresh Vegetables
            {
                "cat_names": ["Fresh Vegetables"],
                "parent_names": ["Fruits & Vegetables"],
                "name_en": "Potato Regular (Alu) 1kg",
                "name_bn": "গোল আলু ১ কেজি",
                "brand": "MetroBazar Fresh",
                "unit": "1 kg",
                "base_price": 55.00,
                "image": "https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=600&auto=format&fit=crop&q=80",
                "description": "Fresh round potatoes.",
            },
            {
                "cat_names": ["Fresh Vegetables"],
                "parent_names": ["Fruits & Vegetables"],
                "name_en": "Onion Local (Deshi Peyaj) 1kg",
                "name_bn": "দেশি পেঁয়াজ ১ কেজি",
                "brand": "MetroBazar Fresh",
                "unit": "1 kg",
                "base_price": 110.00,
                "image": "https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=600&auto=format&fit=crop&q=80",
                "description": "Fresh local Bangladeshi red onions.",
            },
            {
                "cat_names": ["Fresh Vegetables"],
                "parent_names": ["Fruits & Vegetables"],
                "name_en": "Tomato Ripe Red 1kg",
                "name_bn": "টমেটো ১ কেজি",
                "brand": "MetroBazar Fresh",
                "unit": "1 kg",
                "base_price": 80.00,
                "image": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=600&auto=format&fit=crop&q=80",
                "description": "Juicy ripe red tomatoes.",
            },

            # Fresh Fruits
            {
                "cat_names": ["Fresh Fruits"],
                "parent_names": ["Fruits & Vegetables"],
                "name_en": "Green Apple Imported 1kg",
                "name_bn": "সবুজ আপেল ১ কেজি",
                "brand": "MetroBazar Fresh",
                "unit": "1 kg",
                "base_price": 320.00,
                "image": "https://images.unsplash.com/photo-1619546813926-a78fa6372cd2?w=600&auto=format&fit=crop&q=80",
                "description": "Crispy sweet green apples.",
            },
            {
                "cat_names": ["Fresh Fruits"],
                "parent_names": ["Fruits & Vegetables"],
                "name_en": "Banana Sagar (Sagor Kola) 12 pcs",
                "name_bn": "সাগর কলা ১২ টি",
                "brand": "MetroBazar Fresh",
                "unit": "12 pcs",
                "base_price": 110.00,
                "image": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=600&auto=format&fit=crop&q=80",
                "description": "Fresh sweet Sagar bananas.",
            },

            # Organic Produce
            {
                "cat_names": ["Organic Produce"],
                "parent_names": ["Fruits & Vegetables"],
                "name_en": "Organic Hydroponic Lettuce (200g)",
                "name_bn": "অর্গানিক হাইড্রোপনিক লেটুস ২০০ গ্রাম",
                "brand": "MetroBazar Organic",
                "unit": "200 gm",
                "base_price": 120.00,
                "image": "https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?w=600&auto=format&fit=crop&q=80",
                "description": "Pesticide-free fresh green lettuce leaves.",
            },

            # =========================================================
            # MEAT & FISH
            # =========================================================
            # Chicken & Poultry
            {
                "cat_names": ["Chicken & Poultry"],
                "parent_names": ["Meat & Fish"],
                "name_en": "Broiler Whole Chicken Leg Skin On (± 50 gm)",
                "name_bn": "ব্রয়লার মুরগি লেগ স্কিন সহ (± ৫০ গ্রাম)",
                "brand": "Bengal Meat",
                "unit": "1 kg",
                "base_price": 519.00,
                "image": "https://images.unsplash.com/photo-1587593810167-a84920ea0781?w=600&auto=format&fit=crop&q=80",
                "description": "Farm-fresh cleaned broiler chicken legs.",
            },
            {
                "cat_names": ["Chicken & Poultry"],
                "parent_names": ["Meat & Fish"],
                "name_en": "Whole Deshi Chicken Skin Off ± 25 gm",
                "name_bn": "দেশি মুরগি চামড়া ছাড়া ± ২৫ গ্রাম",
                "brand": "Bengal Meat",
                "unit": "500 gm",
                "base_price": 639.00,
                "image": "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=600&auto=format&fit=crop&q=80",
                "description": "Cleaned fresh country deshi chicken.",
            },

            # Beef & Mutton / Meat
            {
                "cat_names": ["Beef & Mutton", "Meat"],
                "parent_names": ["Meat & Fish"],
                "name_en": "Beef Boneless Premium ± 50 gm",
                "name_bn": "গরুর মাংস বোনলেস প্রিমিয়াম ± ৫০ গ্রাম",
                "brand": "Bengal Meat",
                "unit": "1 kg",
                "base_price": 799.00,
                "image": "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&auto=format&fit=crop&q=80",
                "description": "100% fresh boneless lean beef cuts.",
            },
            {
                "cat_names": ["Beef & Mutton", "Meat"],
                "parent_names": ["Meat & Fish"],
                "name_en": "Bengal Meat Mutton Boneless Cut",
                "name_bn": "বেঙ্গল মিট খাসির মাংস বোনলেস",
                "brand": "Bengal Meat",
                "unit": "1 kg",
                "base_price": 1150.00,
                "image": "https://images.unsplash.com/photo-1603048588665-791ca8aea617?w=600&auto=format&fit=crop&q=80",
                "description": "Fresh premium goat mutton cuts.",
            },

            # Fresh & Frozen Fish / Frozen Fish
            {
                "cat_names": ["Fresh & Frozen Fish", "Frozen Fish"],
                "parent_names": ["Meat & Fish"],
                "name_en": "Rui Fish Cleaned Cut (Frozen)",
                "name_bn": "রুই মাছ প্রসেসড কাট (ফ্রোজেন)",
                "brand": "Bengal Meat",
                "unit": "1 kg",
                "base_price": 450.00,
                "image": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&auto=format&fit=crop&q=80",
                "description": "Cleaned scaled sliced Rui fish.",
            },
            {
                "cat_names": ["Fresh & Frozen Fish", "Frozen Fish"],
                "parent_names": ["Meat & Fish"],
                "name_en": "Prawn Large Cleaned (Frozen)",
                "name_bn": "গলদা চিংড়ি পরিষ্কার করা (ফ্রোজেন)",
                "brand": "Bengal Meat",
                "unit": "500 gm",
                "base_price": 680.00,
                "image": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?w=600&auto=format&fit=crop&q=80",
                "description": "Deveined clean giant tiger prawns.",
            },

            # Dried Fish (Shutki)
            {
                "cat_names": ["Dried Fish (Shutki)"],
                "parent_names": ["Meat & Fish"],
                "name_en": "Loitta Dried Fish (Loitta Shutki) 250g",
                "name_bn": "লইট্টা শুঁটকি ২৫০ গ্রাম",
                "brand": "CoxBazar Direct",
                "unit": "250 gm",
                "base_price": 240.00,
                "image": "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=600&auto=format&fit=crop&q=80",
                "description": "Sun dried authentic Loitta fish from Cox's Bazar.",
            },

            # =========================================================
            # DAIRY & BREAKFAST / DAIRY & EGGS
            # =========================================================
            # Farm Fresh Eggs
            {
                "cat_names": ["Farm Fresh Eggs"],
                "parent_names": ["Dairy & Breakfast", "Dairy & Eggs"],
                "name_en": "Layer Chicken Eggs Red 12 Pcs",
                "name_bn": "লাল ডিম ১২ টি",
                "brand": "Aarong Dairy",
                "unit": "12 pcs",
                "base_price": 155.00,
                "image": "https://images.unsplash.com/photo-1516448620398-c5f44bf9f441?w=600&auto=format&fit=crop&q=80",
                "description": "Farm fresh layer chicken red eggs.",
            },

            # Liquid & Powder Milk / Liquid Milk
            {
                "cat_names": ["Liquid & Powder Milk", "Liquid Milk"],
                "parent_names": ["Dairy & Breakfast", "Dairy & Eggs"],
                "name_en": "Aarong Dairy Pasteurized Liquid Milk 1L",
                "name_bn": "আড়ং ডেইরি তরল দুধ ১ লিটার",
                "brand": "Aarong Dairy",
                "unit": "1 L",
                "base_price": 95.00,
                "image": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=600&auto=format&fit=crop&q=80",
                "description": "Pure pasteurized whole milk.",
            },
            {
                "cat_names": ["Liquid & Powder Milk", "Liquid Milk"],
                "parent_names": ["Dairy & Breakfast", "Dairy & Eggs"],
                "name_en": "Dano Full Cream Milk Powder 500g",
                "name_bn": "ডানো ফুল ক্রিম মিল্ক পাউডার ৫০০ গ্রাম",
                "brand": "Dano",
                "unit": "500 gm",
                "base_price": 460.00,
                "image": "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=600&auto=format&fit=crop&q=80",
                "description": "Instant full cream milk powder.",
            },

            # Butter, Cheese & Yogurt / Butter & Ghee
            {
                "cat_names": ["Butter, Cheese & Yogurt", "Butter & Ghee"],
                "parent_names": ["Dairy & Breakfast", "Dairy & Eggs"],
                "name_en": "Aarong Pure Premium Ghee 200g",
                "name_bn": "আড়ং খাঁটি ঘি ২০০ গ্রাম",
                "brand": "Aarong Dairy",
                "unit": "200 gm",
                "base_price": 340.00,
                "image": "https://images.unsplash.com/photo-1631451095765-2c91616fc9e6?w=600&auto=format&fit=crop&q=80",
                "description": "Aromatic 100% pure butter ghee.",
            },

            # Bread, Toast & Bakery / Breakfast
            {
                "cat_names": ["Bread, Toast & Bakery", "Breakfast"],
                "parent_names": ["Dairy & Breakfast", "Food"],
                "name_en": "Milk Bread Family Size 400g",
                "name_bn": "মিল্ক পাউরুটি ৪০০ গ্রাম",
                "brand": "All Time",
                "unit": "400 gm",
                "base_price": 85.00,
                "image": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&auto=format&fit=crop&q=80",
                "description": "Fresh soft sliced milk bread.",
            },

            # Cereals & Oats
            {
                "cat_names": ["Cereals & Oats", "Breakfast"],
                "parent_names": ["Dairy & Breakfast", "Food"],
                "name_en": "Quaker Quick Cooking Oats 500g",
                "name_bn": "কোয়েকার ওটস ৫০০ গ্রাম",
                "brand": "Quaker",
                "unit": "500 gm",
                "base_price": 360.00,
                "image": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&auto=format&fit=crop&q=80",
                "description": "Healthy 100% wholegrain quick cooking oats.",
            },

            # =========================================================
            # SNACKS & BEVERAGES
            # =========================================================
            # Biscuits & Cookies
            {
                "cat_names": ["Biscuits & Cookies", "Snacks & Sweets"],
                "parent_names": ["Snacks & Beverages", "Food"],
                "name_en": "Lexus Vegetable Crackers 200g",
                "name_bn": "লেকসাস ভেজিটেবল বিস্কুট ২০০ গ্রাম",
                "brand": "Munchy's",
                "unit": "200 gm",
                "base_price": 65.00,
                "image": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&auto=format&fit=crop&q=80",
                "description": "Crispy vegetable salted crackers.",
            },

            # Tea & Coffee
            {
                "cat_names": ["Tea & Coffee"],
                "parent_names": ["Snacks & Beverages", "Food"],
                "name_en": "Ispahani Mirzapore Tea Premium Bag 400g",
                "name_bn": "ইস্পাহানি মির্জাপুর চা ৪০০ গ্রাম",
                "brand": "Ispahani",
                "unit": "400 gm",
                "base_price": 210.00,
                "image": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=600&auto=format&fit=crop&q=80",
                "description": "Rich flavor premium black tea blend.",
            },
            {
                "cat_names": ["Tea & Coffee"],
                "parent_names": ["Snacks & Beverages", "Food"],
                "name_en": "Nestle Nescafe 3 in 1 Iced Frappe Cold Coffee",
                "name_bn": "নেসকাফে ৩ ইন ১ কোল্ড কফি",
                "brand": "Nestle",
                "unit": "30 gm",
                "base_price": 50.00,
                "image": "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?w=600&auto=format&fit=crop&q=80",
                "description": "Instant iced cold coffee sachet.",
            },

            # Chips & Chanachur
            {
                "cat_names": ["Chips & Chanachur", "Snacks & Sweets"],
                "parent_names": ["Snacks & Beverages", "Food"],
                "name_en": "Ruchi Hot Chanachur 300g",
                "name_bn": "রুচি হট চানাচুর ৩০০ গ্রাম",
                "brand": "Square",
                "unit": "300 gm",
                "base_price": 75.00,
                "image": "https://images.unsplash.com/photo-1621447504864-d8686e12698c?w=600&auto=format&fit=crop&q=80",
                "description": "Spicy crispy traditional chanachur.",
            },

            # Noodles & Pasta
            {
                "cat_names": ["Noodles & Pasta"],
                "parent_names": ["Snacks & Beverages"],
                "name_en": "Maggi 2-Minute Masala Instant Noodles 8 Pack",
                "name_bn": "ম্যাগি ২ মিনিট নুডুলস ৮ প্যাক",
                "brand": "Nestle",
                "unit": "1 pack",
                "base_price": 160.00,
                "image": "https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=600&auto=format&fit=crop&q=80",
                "description": "Classic 2-minute masala instant noodles.",
            },

            # Chocolates & Candies
            {
                "cat_names": ["Chocolates & Candies"],
                "parent_names": ["Snacks & Beverages"],
                "name_en": "Cadbury Dairy Milk Silk Chocolate 150g",
                "name_bn": "ক্যাডবেরি ডেয়ারি মিল্ক সিল্ক ১৫০ গ্রাম",
                "brand": "Cadbury",
                "unit": "150 gm",
                "base_price": 260.00,
                "image": "https://images.unsplash.com/photo-1548907040-4baa42d10919?w=600&auto=format&fit=crop&q=80",
                "description": "Smooth milk chocolate bar.",
            },

            # Soft Drinks & Juices
            {
                "cat_names": ["Soft Drinks & Juices"],
                "parent_names": ["Snacks & Beverages"],
                "name_en": "Coca-Cola Original Taste Pet Bottle 1.25L",
                "name_bn": "কোকাকোলা ১.২৫ লিটার",
                "brand": "Coca-Cola",
                "unit": "1 L",
                "base_price": 90.00,
                "image": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&auto=format&fit=crop&q=80",
                "description": "Refreshing carbonated soft drink.",
            },

            # =========================================================
            # CLEANING & HOUSEHOLD / CLEANING SUPPLIES
            # =========================================================
            # Dishwashing Supplies
            {
                "cat_names": ["Dishwashing Supplies", "Household"],
                "parent_names": ["Cleaning & Household", "Cleaning Supplies"],
                "name_en": "Vim Dishwash Liquid Lemon 500ml",
                "name_bn": "ভিম ডিশওয়াশ লিকুইড ৫০০ মিলি",
                "brand": "Unilever",
                "unit": "500 ml",
                "base_price": 135.00,
                "image": "https://images.unsplash.com/photo-1585832770485-e68a5fcfad52?w=600&auto=format&fit=crop&q=80",
                "description": "Lemon grease cutting dishwashing liquid.",
            },

            # Laundry Detergent & Soap / Laundry & Detergents
            {
                "cat_names": ["Laundry Detergent & Soap", "Laundry & Detergents"],
                "parent_names": ["Cleaning & Household", "Cleaning Supplies"],
                "name_en": "Surf Excel Quick Wash Detergent Powder 1kg",
                "name_bn": "সার্ফ এক্সেল ওয়াশিং পাউডার ১ কেজি",
                "brand": "Unilever",
                "unit": "1 kg",
                "base_price": 220.00,
                "image": "https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?w=600&auto=format&fit=crop&q=80",
                "description": "Stain removing detergent powder.",
            },

            # Toilet & Floor Cleaners / Toilet Cleaners
            {
                "cat_names": ["Toilet & Floor Cleaners", "Toilet Cleaners"],
                "parent_names": ["Cleaning & Household", "Cleaning Supplies"],
                "name_en": "Harpic Liquid Toilet Cleaner Original 750ml",
                "name_bn": "হারপিক টয়লেট ক্লিনার ৭৫০ মিলি",
                "brand": "Reckitt",
                "unit": "750 ml",
                "base_price": 185.00,
                "image": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&auto=format&fit=crop&q=80",
                "description": "Disinfectant liquid toilet cleaner.",
            },

            # Air Fresheners & Insect Control / Household
            {
                "cat_names": ["Air Fresheners & Insect Control", "Household"],
                "parent_names": ["Cleaning & Household", "Cleaning Supplies"],
                "name_en": "ACI Insecticide Aerosol Mosquito Spray 475ml",
                "name_bn": "এসিআই এরোসল ৪৭৫ মিলি",
                "brand": "ACI",
                "unit": "1 pc",
                "base_price": 340.00,
                "image": "https://images.unsplash.com/photo-1628102491629-778571d893a3?w=600&auto=format&fit=crop&q=80",
                "description": "Fast action mosquito & insect killer spray.",
            },

            # =========================================================
            # PERSONAL CARE & HEALTH / PERSONAL CARE
            # =========================================================
            # Bath & Body Soap
            {
                "cat_names": ["Bath & Body Soap"],
                "parent_names": ["Personal Care & Health", "Personal Care"],
                "name_en": "Lux Velvet Touch Body Soap 150g",
                "name_bn": "লাক্স ভেলভেট সাবান ১৫০ গ্রাম",
                "brand": "Unilever",
                "unit": "150 gm",
                "base_price": 75.00,
                "image": "https://images.unsplash.com/photo-1600857544200-b2f666a9a2ec?w=600&auto=format&fit=crop&q=80",
                "description": "Fragrant bathing soap with jasmine extract.",
            },

            # Hair Care & Shampoo / Hair Care
            {
                "cat_names": ["Hair Care & Shampoo", "Hair Care"],
                "parent_names": ["Personal Care & Health", "Personal Care"],
                "name_en": "Sunsilk Thick & Long Shampoo 375ml",
                "name_bn": "সানসিল্ক শ্যাম্পু ৩৭৫ মিলি",
                "brand": "Unilever",
                "unit": "375 ml",
                "base_price": 360.00,
                "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=600&auto=format&fit=crop&q=80",
                "description": "Nourishing shampoo for thick long hair.",
            },
            {
                "cat_names": ["Hair Care & Shampoo", "Hair Care"],
                "parent_names": ["Personal Care & Health", "Personal Care"],
                "name_en": "Tibet Pumpkin Hair Oil Pure Herbal 200ml",
                "name_bn": "তিব্বত পাম্পকিন হেয়ার অয়েল ২০০ মিলি",
                "brand": "Tibet",
                "unit": "200 ml",
                "base_price": 240.00,
                "image": "https://images.unsplash.com/photo-1608248597359-00984a9191d9?w=600&auto=format&fit=crop&q=80",
                "description": "Herbal pumpkin seed extract hair oil.",
            },

            # Oral Care & Toothpaste
            {
                "cat_names": ["Oral Care & Toothpaste"],
                "parent_names": ["Personal Care & Health", "Personal Care"],
                "name_en": "Close Up Red Hot Gel Toothpaste 140g",
                "name_bn": "ক্লোজআপ রেড হট টুথপেস্ট ১৪০ গ্রাম",
                "brand": "Unilever",
                "unit": "140 gm",
                "base_price": 125.00,
                "image": "https://images.unsplash.com/photo-1559598467-f8b76c8155d0?w=600&auto=format&fit=crop&q=80",
                "description": "Fresh breath red gel toothpaste.",
            },

            # Skin Care & Creams
            {
                "cat_names": ["Skin Care & Creams"],
                "parent_names": ["Personal Care & Health", "Personal Care"],
                "name_en": "Nivea Soft Refreshing Moisturizing Cream 100ml",
                "name_bn": "নিভিয়া সফট ময়েশ্চারাইজিং ক্রিম ১০০ মিলি",
                "brand": "Nivea",
                "unit": "100 ml",
                "base_price": 290.00,
                "image": "https://images.unsplash.com/photo-1608248597359-00984a9191d9?w=600&auto=format&fit=crop&q=80",
                "description": "Light moisturizing skin cream with jojoba oil.",
            },

            # =========================================================
            # BABY CARE
            # =========================================================
            # Baby Diapers & Wipes / Diapers & Wipes
            {
                "cat_names": ["Baby Diapers & Wipes", "Diapers & Wipes"],
                "parent_names": ["Baby Care"],
                "name_en": "NeoCare Premium Baby Diaper Belt S (3-6 kg) 50 pcs",
                "name_bn": "নিওকেয়ার বেবি ডায়াপার বেল্ট S ৫০ টি",
                "brand": "NeoCare",
                "unit": "50 pcs",
                "base_price": 950.00,
                "image": "https://images.unsplash.com/photo-1519689680058-324335c77eba?w=600&auto=format&fit=crop&q=80",
                "description": "Soft breathable belt diaper for newborns.",
            },

            # Baby Food & Formula / Baby Food
            {
                "cat_names": ["Baby Food & Formula", "Baby Food"],
                "parent_names": ["Baby Care"],
                "name_en": "Mother's Smile Prima 1 Milk Tin (0-6 months) 400g",
                "name_bn": "মাদার্স স্মাইল প্রিমা ১ ইনফ্যান্ট ফর্মুলা ৪০০ গ্রাম",
                "brand": "Mother's Smile",
                "unit": "400 gm",
                "base_price": 720.00,
                "image": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=600&auto=format&fit=crop&q=80",
                "description": "Infant milk formula for 0-6 months baby.",
            },
        ]

        count = 0
        all_categories = list(Category.objects.all())

        for item in PRODUCTS_DATA:
            # Find all matching category objects in DB that match any of cat_names
            target_categories = []

            for cat_name in item["cat_names"]:
                matches = [c for c in all_categories if c.name_en.strip().lower() == cat_name.strip().lower()]
                if not matches:
                    # If category doesn't exist, create it under first parent name
                    parent_name = item["parent_names"][0]
                    parent_cat = next((c for c in all_categories if c.name_en.strip().lower() == parent_name.strip().lower()), None)
                    if not parent_cat:
                        parent_cat = Category.objects.create(
                            name_en=parent_name,
                            slug=slugify(parent_name),
                            is_active=True
                        )
                        all_categories.append(parent_cat)

                    new_cat = Category.objects.create(
                        name_en=cat_name,
                        slug=slugify(cat_name),
                        parent=parent_cat,
                        is_active=True
                    )
                    all_categories.append(new_cat)
                    target_categories.append(new_cat)
                else:
                    target_categories.extend(matches)

            # De-duplicate matching target categories
            unique_target_categories = {c.id: c for c in target_categories}.values()

            for category in unique_target_categories:
                product_sku = f"SKU-MB-{uuid.uuid4().hex[:8].upper()}"
                product = Product.objects.create(
                    category=category,
                    name_en=item["name_en"],
                    name_bn=item["name_bn"],
                    sku=product_sku,
                    brand=item["brand"],
                    unit=item["unit"],
                    base_price=item["base_price"],
                    image=item["image"],
                    description=item["description"],
                    is_active=True,
                )

                ProductInventory.objects.create(
                    dark_store=dark_store,
                    product=product,
                    stock_qty=100,
                    store_price=item["base_price"],
                    is_available=True,
                )

                count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created Product ID {product.id}: {product.name_en} under Category '{category.name_en}'"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Successfully seeded {count} authentic real products covering ALL categories & subcategories into backend database!"))
