try:
    from .database import Address, Base, CartItem, Product, Purchase, Review, Store, StoreCategory, User, engine, SessionLocal
except ImportError:
    from database import Address, Base, CartItem, Product, Purchase, Review, Store, StoreCategory, User, engine, SessionLocal


PRODUCTS = [
    {
        "name": "Meja Kerja Astra Pro",
        "description": "Meja kerja berdiri berbahan kayu walnut dengan dua motor senyap, preset ketinggian, dan manajemen kabel terintegrasi.",
        "price": 649000.00,
        "image_url": "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?auto=format&fit=crop&w=1200&q=80",
        "category": "Ruang Kerja",
    },
    {
        "name": "Kursi Ergonomis Nimbus",
        "description": "Kursi ergonomis berbahan mesh dengan penyangga lumbar adaptif dan bantalan yang nyaman serta sejuk.",
        "price": 429000.00,
        "image_url": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&w=1200&q=80",
        "category": "Ruang Kerja",
    },
    {
        "name": "Lampu Meja Luma Arc",
        "description": "Lampu meja LED dengan pilihan temperatur warna, diffuser rendah silau, dan kontrol sentuh.",
        "price": 119000.00,
        "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=1200&q=80",
        "category": "Pencahayaan",
    },
    {
        "name": "Cangkir Keramik Forge",
        "description": "Cangkir keramik berdinding ganda dengan alas berbobot dan lapisan matte yang elegan.",
        "price": 34000.00,
        "image_url": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=1200&q=80",
        "category": "Dapur",
    },
    {
        "name": "Headphone Pulse",
        "description": "Headphone nirkabel dengan peredam bising, audio spasial, dan daya tahan baterai sepanjang hari.",
        "price": 249000.00,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=80",
        "category": "Audio",
        "stock": 1,
        "sku": "PULSE-FLASH-1",
    },
    {
        "name": "Tas Ransel Orbit",
        "description": "Tas ransel komuter tahan cuaca dengan perlindungan laptop dan kantong modular.",
        "price": 139000.00,
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=1200&q=80",
        "category": "Perjalanan",
    },
]


REVIEWS = [
    (1, 1, 5, "Mejanya kokoh. Motornya senyap dan tray kabel membuat meja tetap rapi."),
    (2, 1, 4, "Terlihat premium. Perakitannya cukup lama, tetapi permukaannya sangat bagus."),
    (5, 1, 5, "Rentang ketinggiannya cocok untuk meja kerja bersama dan finishing-nya tetap terlihat baru."),
    (1, 2, 5, "Penyangga lumbar-nya sangat nyaman untuk bekerja lama."),
    (3, 3, 4, "Pilihan temperatur warnanya bagus. Alasnya lebih berat dari yang terlihat."),
    (2, 4, 5, "Nyaman digenggam dan bisa menjaga kopi tetap hangat."),
    (4, 5, 5, "Peredam bisingnya kuat dan nyaman dipakai."),
    (5, 6, 3, "Kantongnya berguna, tetapi kantong botol di samping agak sempit."),
]


USERS = [
    (1, "bejo", "Bejo", "password123"),
    (2, "aming", "Aming", "password123"),
    (3, "deon", "Deon", "password123"),
    (4, "ujang", "Ujang", "password123"),
    (5, "asep", "Asep", "password123"),
]


def _insert_seed_data(db) -> None:
    """Insert the unchanged TokTok baseline into an empty database session."""
    db.add_all(
        User(id=user_id, username=username, display_name=display_name, password=password)
        for user_id, username, display_name, password in USERS
    )
    store = Store(
        id=1,
        owner_id=2,
        name="Aming Official Store",
        slug="aming-official-store",
        description="Aming's curated store for workspace, home, audio, and travel essentials.",
        category="Home & Lifestyle",
        city="Jakarta",
        phone="021-555-0142",
        address="Jl. Melati No. 8, Jakarta Selatan",
        opening_hours="Monday–Saturday, 09:00–18:00",
        return_policy="Returns can be requested within 7 days of delivery.",
    )
    db.add(store)
    db.flush()
    categories = {}
    for category_name in sorted({product["category"] for product in PRODUCTS}):
        category = StoreCategory(
            store_id=store.id,
            name=category_name,
            slug=category_name.lower().replace(" ", "-"),
        )
        db.add(category)
        categories[category_name] = category
    db.flush()
    products = [Product(**product, status="active") for product in PRODUCTS]
    for product in products:
        product.store_id = store.id
        product.category_id = categories[product.category].id
    db.add_all(products)
    db.flush()

    db.add_all(
        Review(
            user_id=user_id,
            product_id=product_id,
            rating=rating,
            body=body,
            is_anonymous=user_id == 2 and product_id == 4,
        )
        for user_id, product_id, rating, body in REVIEWS
    )
    db.add_all(
        [
            Purchase(user_id=1, product_id=1, quantity=1, total=649000.00),
            Purchase(user_id=1, product_id=2, quantity=1, total=429000.00),
            Purchase(user_id=1, product_id=4, quantity=2, total=68000.00),
            Purchase(user_id=2, product_id=1, quantity=1, total=649000.00),
            Purchase(user_id=2, product_id=4, quantity=1, total=34000.00),
            Purchase(user_id=3, product_id=3, quantity=1, total=119000.00),
            Purchase(user_id=4, product_id=5, quantity=1, total=249000.00),
            Purchase(user_id=5, product_id=1, quantity=1, total=649000.00),
            Purchase(user_id=5, product_id=5, quantity=1, total=249000.00),
            Purchase(user_id=5, product_id=6, quantity=1, total=139000.00),
            CartItem(user_id=1, product_id=3, quantity=1),
            Address(id=1, user_id=1, label="Rumah", recipient_name="Bejo", phone="081234567801", address_line="Jl. Merdeka No. 10", city="Jakarta", postal_code="10110", is_default=True),
            Address(id=2, user_id=2, label="Kantor", recipient_name="Aming", phone="081234567802", address_line="Jl. Sudirman No. 25", city="Jakarta", postal_code="10220", is_default=True),
        ]
    )


def seed_fresh_install() -> bool:
    """Create missing tables and seed only when the users table is empty."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(User.id).first() is not None:
            return False
        _insert_seed_data(db)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed() -> None:
    """Destructive manual-only development seed; never call from runtime startup."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _insert_seed_data(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seeded shop.db with products, reviews, cart items, and purchase history.")
