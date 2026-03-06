from __future__ import annotations

from pathlib import Path

from sqlalchemy import Float, ForeignKey, Integer, String, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from werkzeug.security import generate_password_hash

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "aung_market.db"
DATABASE_URL = f"sqlite+pysqlite:///{DB_PATH.as_posix()}"

# Shared SQLAlchemy engine/session factory for the whole app.
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
# Simple in-process guard so init work runs once per app process.
_db_ready = False


class Base(DeclarativeBase):
    pass


# ORM models
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String, nullable=False, default="")
    address: Mapped[str] = mapped_column(String, nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    price: Mapped[float] = mapped_column(Float, nullable=False)
    image_path: Mapped[str] = mapped_column(String, nullable=False, default="")
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_featured: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    promotion: Mapped[str] = mapped_column(String, nullable=False)
    channel_sms: Mapped[str] = mapped_column(String, nullable=False, default="N")
    channel_whatsapp: Mapped[str] = mapped_column(String, nullable=False, default="N")
    channel_email: Mapped[str] = mapped_column(String, nullable=False, default="N")
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False, default="")
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False, default="Pending")
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)


def db() -> Session:
    # Use as context manager: `with db() as dbs: ...`
    return SessionLocal()


def init_db() -> None:
    # Create schema and default admin user once at startup.
    global _db_ready
    if _db_ready:
        return

    Base.metadata.create_all(engine)

    with db() as dbs:
        # Lightweight migration for existing SQLite files created before new columns.
        user_cols = [r[1] for r in dbs.execute(text("PRAGMA table_info(users)")).all()]
        if "phone" not in user_cols:
            dbs.execute(text("ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT ''"))
        if "address" not in user_cols:
            dbs.execute(text("ALTER TABLE users ADD COLUMN address TEXT NOT NULL DEFAULT ''"))

        order_cols = [r[1] for r in dbs.execute(text("PRAGMA table_info(orders)")).all()]
        if "address" not in order_cols:
            dbs.execute(text("ALTER TABLE orders ADD COLUMN address TEXT NOT NULL DEFAULT ''"))

        product_cols = [r[1] for r in dbs.execute(text("PRAGMA table_info(products)")).all()]
        if "is_featured" not in product_cols:
            dbs.execute(text("ALTER TABLE products ADD COLUMN is_featured INTEGER NOT NULL DEFAULT 0"))

        dbs.commit()

        admin_exists = dbs.scalar(select(User.id).where(User.is_admin == 1).limit(1))
        if admin_exists is None:
            dbs.add(
                User(
                    name="Admin",
                    email="admin@gmail.com",
                    phone="",
                    address="",
                    password_hash=generate_password_hash("admin123"),
                    is_admin=1,
                )
            )
            dbs.commit()

    _db_ready = True
