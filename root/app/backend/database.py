import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    email = Column(String(254), unique=True, index=True, nullable=True)
    display_name = Column(String(120), nullable=False)
    password = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(80), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    image_url = Column(String(400), nullable=False)
    category = Column(String(80), nullable=False)
    # Nullable keeps the seeded marketplace catalog backwards-compatible.
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("store_categories.id"), nullable=True, index=True)
    # Legacy products have no inventory limit; store-managed products always set stock.
    stock = Column(Integer, nullable=True)
    sku = Column(String(80), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="draft")

    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    questions = relationship("ProductQuestion", back_populates="product", cascade="all, delete-orphan")
    claims = relationship("ProductClaim", back_populates="product", cascade="all, delete-orphan")
    store = relationship("Store", back_populates="products")
    store_category = relationship("StoreCategory", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductQuestion(Base):
    __tablename__ = "product_questions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    answered_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="questions")
    user = relationship("User")


class ProductClaim(Base):
    __tablename__ = "product_claims"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="claimed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="claims")
    user = relationship("User")


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(160), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(80), nullable=False)
    city = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=False)
    logo_url = Column(String(400), nullable=True)
    banner_url = Column(String(400), nullable=True)
    address = Column(String(300), nullable=True)
    opening_hours = Column(Text, nullable=True)
    return_policy = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User")
    products = relationship("Product", back_populates="store")
    categories = relationship("StoreCategory", back_populates="store", cascade="all, delete-orphan")
    discounts = relationship("Discount", back_populates="store", cascade="all, delete-orphan")


class StoreWebhook(Base):
    __tablename__ = "store_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, unique=True, index=True)
    name = Column(String(120), nullable=False, default="Discord notifications")
    url = Column(String(500), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    store = relationship("Store")


class StoreMember(Base):
    __tablename__ = "store_members"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="viewer")
    identity_username = Column(String(80), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    store = relationship("Store")


class StoreExport(Base):
    __tablename__ = "store_exports"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    export_type = Column(String(40), nullable=False, default="orders")
    filename = Column(String(180), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    store = relationship("Store")
    created_by = relationship("User")


class StoreCategory(Base):
    __tablename__ = "store_categories"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    name = Column(String(80), nullable=False)
    slug = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    store = relationship("Store", back_populates="categories")
    products = relationship("Product", back_populates="store_category")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    size = Column(String(60), nullable=True)
    color = Column(String(60), nullable=True)
    sku = Column(String(80), nullable=False, unique=True, index=True)
    stock = Column(Integer, nullable=False, default=0)
    price = Column(Float, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="variants")


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    label = Column(String(80), nullable=False)
    recipient_name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=False)
    address_line = Column(String(300), nullable=False)
    city = Column(String(120), nullable=False)
    postal_code = Column(String(20), nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="addresses")


class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    code = Column(String(40), nullable=False)
    kind = Column(String(20), nullable=False)  # percentage or fixed
    value = Column(Float, nullable=False)
    min_subtotal = Column(Float, nullable=False, default=0)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    usage_limit = Column(Integer, nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    scope = Column(String(20), nullable=False, default="all")  # all, category, or product
    target_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    store = relationship("Store", back_populates="discounts")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price_snapshot = Column(Float, nullable=True)

    product = relationship("Product")
    variant = relationship("ProductVariant")


class CartCheckoutState(Base):
    __tablename__ = "cart_checkout_states"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    shipping_address_id = Column(Integer, ForeignKey("addresses.id"), nullable=False)
    shipping_fee_snapshot = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    shipping_address = relationship("Address")


class CartCouponState(Base):
    __tablename__ = "cart_coupon_states"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    discount_id = Column(Integer, ForeignKey("discounts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    discount = relationship("Discount")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)
    total = Column(Float, nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    discount_code = Column(String(40), nullable=True)
    discount_amount = Column(Float, nullable=False, default=0)
    shipping_fee = Column(Float, nullable=False, default=0)
    shipping_address_id = Column(Integer, ForeignKey("addresses.id"), nullable=True)
    internal_note = Column(Text, nullable=True)

    product = relationship("Product")
    shipping_address = relationship("Address")
    variant = relationship("ProductVariant")
    refund = relationship("Refund", back_populates="purchase", cascade="all, delete-orphan", uselist=False)
    return_request = relationship("ReturnRequest", back_populates="purchase", cascade="all, delete-orphan", uselist=False)


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="requested")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    purchase = relationship("Purchase", back_populates="refund")
    user = relationship("User")


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="requested")
    refund_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    purchase = relationship("Purchase", back_populates="return_request")
    user = relationship("User")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    body = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    entity_type = Column(String(40), nullable=False)
    entity_id = Column(Integer, nullable=True)
    action = Column(String(40), nullable=False)
    changes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def create_db() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_user_email_column()
    ensure_review_anonymous_column()
    ensure_product_store_columns()
    ensure_purchase_status_column()
    ensure_purchase_discount_columns()
    ensure_discount_scope_columns()
    ensure_store_profile_columns()
    ensure_product_catalog_columns()
    ensure_purchase_shipping_column()
    ensure_purchase_internal_note_column()
    ensure_shipping_fee_columns()
    ensure_variant_reference_columns()
    ensure_cart_price_snapshot_column()
    ensure_store_member_columns()
    ensure_default_catalog_localization()
    ensure_default_anonymous_review()
    ensure_default_store_catalog()


def ensure_user_email_column() -> None:
    """Add optional account email support without rebuilding existing user data."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as connection:
        if "email" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(254)"))
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
        )


def ensure_review_anonymous_column() -> None:
    inspector = inspect(engine)
    if "reviews" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("reviews")}
    if "is_anonymous" in columns:
        return
    default_value = "0" if engine.dialect.name == "sqlite" else "FALSE"
    with engine.begin() as connection:
        connection.execute(
            text(f"ALTER TABLE reviews ADD COLUMN is_anonymous BOOLEAN NOT NULL DEFAULT {default_value}")
        )


def ensure_product_store_columns() -> None:
    """Add marketplace columns to existing lab databases without dropping data."""
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("products")}
    statements = {
        "store_id": "ALTER TABLE products ADD COLUMN store_id INTEGER",
        "category_id": "ALTER TABLE products ADD COLUMN category_id INTEGER",
        "stock": "ALTER TABLE products ADD COLUMN stock INTEGER",
    }
    with engine.begin() as connection:
        for column, statement in statements.items():
            if column not in columns:
                connection.execute(text(statement))


def ensure_purchase_status_column() -> None:
    inspector = inspect(engine)
    if "purchases" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("purchases")}
    if "status" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE purchases ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'pending'"))


def ensure_purchase_discount_columns() -> None:
    inspector = inspect(engine)
    if "purchases" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("purchases")}
    statements = {
        "discount_code": "ALTER TABLE purchases ADD COLUMN discount_code VARCHAR(40)",
        "discount_amount": "ALTER TABLE purchases ADD COLUMN discount_amount FLOAT NOT NULL DEFAULT 0",
    }
    with engine.begin() as connection:
        for column, statement in statements.items():
            if column not in columns:
                connection.execute(text(statement))


def ensure_discount_scope_columns() -> None:
    inspector = inspect(engine)
    if "discounts" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("discounts")}
    statements = {
        "scope": "ALTER TABLE discounts ADD COLUMN scope VARCHAR(20) NOT NULL DEFAULT 'all'",
        "target_id": "ALTER TABLE discounts ADD COLUMN target_id INTEGER",
    }
    with engine.begin() as connection:
        for column, statement in statements.items():
            if column not in columns:
                connection.execute(text(statement))


def ensure_store_profile_columns() -> None:
    inspector = inspect(engine)
    if "stores" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("stores")}
    statements = {
        "logo_url": "ALTER TABLE stores ADD COLUMN logo_url VARCHAR(400)",
        "banner_url": "ALTER TABLE stores ADD COLUMN banner_url VARCHAR(400)",
        "address": "ALTER TABLE stores ADD COLUMN address VARCHAR(300)",
        "opening_hours": "ALTER TABLE stores ADD COLUMN opening_hours TEXT",
        "return_policy": "ALTER TABLE stores ADD COLUMN return_policy TEXT",
    }
    with engine.begin() as connection:
        for column, statement in statements.items():
            if column not in columns:
                connection.execute(text(statement))


def ensure_product_catalog_columns() -> None:
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("products")}
    statements = {
        "sku": "ALTER TABLE products ADD COLUMN sku VARCHAR(80)",
        "status": "ALTER TABLE products ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'",
    }
    with engine.begin() as connection:
        for column, statement in statements.items():
            if column not in columns:
                connection.execute(text(statement))


def ensure_purchase_shipping_column() -> None:
    inspector = inspect(engine)
    if "purchases" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("purchases")}
    if "shipping_address_id" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE purchases ADD COLUMN shipping_address_id INTEGER"))


def ensure_purchase_internal_note_column() -> None:
    inspector = inspect(engine)
    if "purchases" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("purchases")}
    if "internal_note" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE purchases ADD COLUMN internal_note TEXT"))


def ensure_shipping_fee_columns() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "purchases" in tables:
        columns = {column["name"] for column in inspector.get_columns("purchases")}
        with engine.begin() as connection:
            if "shipping_fee" not in columns and "tax_amount" in columns:
                connection.execute(text("ALTER TABLE purchases RENAME COLUMN tax_amount TO shipping_fee"))
            elif "shipping_fee" not in columns:
                connection.execute(text("ALTER TABLE purchases ADD COLUMN shipping_fee FLOAT NOT NULL DEFAULT 0"))

    if "cart_checkout_states" in tables:
        columns = {column["name"] for column in inspector.get_columns("cart_checkout_states")}
        with engine.begin() as connection:
            if "shipping_fee_snapshot" not in columns:
                if "tax_amount_snapshot" in columns:
                    connection.execute(text(
                        "ALTER TABLE cart_checkout_states RENAME COLUMN tax_amount_snapshot TO shipping_fee_snapshot"
                    ))
                else:
                    connection.execute(text(
                        "ALTER TABLE cart_checkout_states ADD COLUMN shipping_fee_snapshot FLOAT NOT NULL DEFAULT 0"
                    ))
            if "tax_rate_snapshot" in columns:
                connection.execute(text("ALTER TABLE cart_checkout_states DROP COLUMN tax_rate_snapshot"))


def ensure_variant_reference_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in ("cart_items", "purchases"):
            if table not in inspector.get_table_names():
                continue
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "variant_id" not in columns:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN variant_id INTEGER"))


def ensure_cart_price_snapshot_column() -> None:
    inspector = inspect(engine)
    if "cart_items" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("cart_items")}
    if "unit_price_snapshot" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE cart_items ADD COLUMN unit_price_snapshot FLOAT"))

    db = SessionLocal()
    try:
        items = db.query(CartItem).filter(CartItem.unit_price_snapshot.is_(None)).all()
        for item in items:
            variant = db.get(ProductVariant, item.variant_id) if item.variant_id else None
            product = db.get(Product, item.product_id)
            if product:
                item.unit_price_snapshot = variant.price if variant and variant.price is not None else product.price
        if items:
            db.commit()
    finally:
        db.close()


def ensure_store_member_columns() -> None:
    inspector = inspect(engine)
    if "store_members" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("store_members")}
    if "active" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE store_members ADD COLUMN active BOOLEAN NOT NULL DEFAULT 1"))
    if "identity_username" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE store_members ADD COLUMN identity_username VARCHAR(80)")
            )


def ensure_default_catalog_localization() -> None:
    """Localize the original demo catalog without replacing user-created data."""
    legacy_catalog = {
        "AstraDesk Pro": {
            "name": "Meja Kerja Astra Pro",
            "description": "Meja kerja berdiri berbahan kayu walnut dengan dua motor senyap, preset ketinggian, dan manajemen kabel terintegrasi.",
            "price": 649000.0,
            "category": "Ruang Kerja",
        },
        "Nimbus Ergonomic Chair": {
            "name": "Kursi Ergonomis Nimbus",
            "description": "Kursi ergonomis berbahan mesh dengan penyangga lumbar adaptif dan bantalan yang nyaman serta sejuk.",
            "price": 429000.0,
            "category": "Ruang Kerja",
        },
        "Luma Arc Desk Lamp": {
            "name": "Lampu Meja Luma Arc",
            "description": "Lampu meja LED dengan pilihan temperatur warna, diffuser rendah silau, dan kontrol sentuh.",
            "price": 119000.0,
            "category": "Pencahayaan",
        },
        "Forge Ceramic Mug": {
            "name": "Cangkir Keramik Forge",
            "description": "Cangkir keramik berdinding ganda dengan alas berbobot dan lapisan matte yang elegan.",
            "price": 34000.0,
            "category": "Dapur",
        },
        "Pulse Headphones": {
            "name": "Headphone Pulse",
            "description": "Headphone nirkabel dengan peredam bising, audio spasial, dan daya tahan baterai sepanjang hari.",
            "price": 249000.0,
            "category": "Audio",
        },
        "Orbit Commuter Backpack": {
            "name": "Tas Ransel Orbit",
            "description": "Tas ransel komuter tahan cuaca dengan perlindungan laptop dan kantong modular.",
            "price": 139000.0,
            "category": "Perjalanan",
        },
    }
    db = SessionLocal()
    try:
        products = db.query(Product).filter(Product.name.in_(legacy_catalog)).all()
        for product in products:
            legacy = legacy_catalog[product.name]
            product.name = legacy["name"]
            product.description = legacy["description"]
            product.price = legacy["price"]
            product.category = legacy["category"]
            product.status = product.status or "active"
        if products:
            db.commit()
    finally:
        db.close()


def ensure_default_anonymous_review() -> None:
    """Keep the seeded Aming review for product 4 anonymous."""
    db = SessionLocal()
    try:
        review = (
            db.query(Review)
            .filter(Review.user_id == 2, Review.product_id == 4)
            .first()
        )
        if review and not review.is_anonymous:
            review.is_anonymous = True
            db.commit()
    finally:
        db.close()


def ensure_default_store_catalog() -> None:
    """Attach the seeded catalog to Aming's public store without touching custom stores."""
    db = SessionLocal()
    try:
        owner = db.get(User, 2)
        if not owner:
            return
        store = db.query(Store).filter(Store.owner_id == owner.id).first()
        if not store:
            store = Store(
                owner_id=owner.id,
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
        elif store.name == "Aming Official Store" and store.description.startswith("Toko pilihan"):
            store.description = "Aming's curated store for workspace, home, audio, and travel essentials."
            store.category = "Home & Lifestyle"
            store.opening_hours = "Monday–Saturday, 09:00–18:00"
            store.return_policy = "Returns can be requested within 7 days of delivery."
        category_map = {}
        for name in db.query(Product.category).filter(Product.store_id.is_(None)).distinct().all():
            category_name = name[0]
            category = db.query(StoreCategory).filter(StoreCategory.store_id == store.id, StoreCategory.name == category_name).first()
            if not category:
                category = StoreCategory(store_id=store.id, name=category_name, slug=category_name.lower().replace(" ", "-"))
                db.add(category)
                db.flush()
            category_map[category_name] = category
        for product in db.query(Product).filter(Product.store_id.is_(None)).all():
            category = category_map.get(product.category)
            if category:
                product.store_id = store.id
                product.category_id = category.id
        db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
