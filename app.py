from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import *
from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import Feedback, Order, OrderItem, Product, User, db, init_db

# Local paths used by upload and static file operations.
APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "static" / "assets" / "images" / "menu_uploads"

# Allowed extensions for uploaded product images.
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
ORDER_STATUSES = ("Pending", "Confirmed", "Preparing", "Out for Delivery", "Completed", "Cancelled")
DEFAULT_PRODUCT_CATEGORIES = ("Watches", "Jewelry", "Bags", "Sunglasses", "Perfume")
DEFAULT_SORT = "featured"

app = Flask(__name__)
app.secret_key = "dev"  # change for production


@app.before_request
def _ensure_db() -> None:
    # Keep upload target available and initialize DB schema/seed data lazily.
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()


@dataclass
class CurrentUser:
    # Session-friendly user view to avoid passing ORM objects into session state.
    id: int
    name: str
    email: str
    phone: str
    address: str
    is_admin: bool


def get_current_user() -> CurrentUser | None:
    uid = session.get("user_id")
    if not uid:
        return None

    with db() as dbs:
        user = dbs.get(User, int(uid))

    if not user:
        session.pop("user_id", None)
        return None

    return CurrentUser(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone or "",
        address=user.address or "",
        is_admin=bool(user.is_admin),
    )


@app.context_processor
def inject_globals() -> dict[str, Any]:
    return {
        "current_user": get_current_user(),
        "now_year": datetime.now().year,
        "status_class": status_class,
    }


# Cart is stored in Flask session as {product_id: {product_id, name, price, quantity}}.
def cart_get() -> dict[str, Any]:
    return session.get("cart", {})


def cart_save(cart: dict[str, Any]) -> None:
    session["cart"] = cart
    session.modified = True


def cart_total(cart: dict[str, Any]) -> float:
    total = 0.0
    for _, item in cart.items():
        total += float(item["price"]) * int(item["quantity"])
    return total


def allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXT


def status_class(status: str) -> str:
    return f"status-{(status or '').strip().lower().replace(' ', '-')}"


def get_local_redirect(default_endpoint: str = "menu") -> str:
    target = (request.form.get("next") or request.args.get("next") or "").strip()
    if target.startswith("/") and not target.startswith("//"):
        return target
    return url_for(default_endpoint)


# Public storefront routes
@app.get("/")
def home():
    with db() as dbs:
        featured = dbs.execute(
            select(Product)
            .where(Product.is_active == 1, Product.is_featured == 1)
            .order_by(Product.created_at.desc())
            .limit(6)
        ).scalars().all()

    return render_template(
        "home.html",
        title="Aung Market",
        featuredItems=featured,
    )


@app.get("/menu")
def menu():
    with db() as dbs:
        categories = dbs.execute(
            select(Product.category).where(Product.is_active == 1).distinct().order_by(Product.category.asc())
        ).scalars().all()

        search = (request.args.get("q") or "").strip()
        category = (request.args.get("category") or "").strip()
        sort = (request.args.get("sort") or DEFAULT_SORT).strip()

        query = select(Product).where(Product.is_active == 1)

        if search:
            term = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(Product.name).like(term),
                    func.lower(Product.description).like(term),
                    func.lower(Product.category).like(term),
                )
            )

        if category:
            query = query.where(func.lower(Product.category) == category.lower())

        order_map: dict[str, tuple[Any, ...]] = {
            "featured": (desc(Product.is_featured), Product.category.asc(), Product.name.asc()),
            "price_asc": (Product.price.asc(), Product.name.asc()),
            "price_desc": (Product.price.desc(), Product.name.asc()),
            "newest": (Product.created_at.desc(), Product.name.asc()),
            "name": (Product.name.asc(),),
        }
        order_clauses = order_map.get(sort, order_map[DEFAULT_SORT])
        rows = dbs.execute(query.order_by(*order_clauses))
        items = rows.scalars().all()

    return render_template(
        "menu.html",
        title="Take Order - Aung Market",
        items=items,
        categories=categories,
        selected_category=category,
        search_query=search,
        current_sort=sort,
    )


@app.get("/products/<int:product_id>")
def product_detail(product_id: int):
    with db() as dbs:
        product = dbs.execute(
            select(Product).where(Product.id == product_id, Product.is_active == 1)
        ).scalars().all()
        product = product[0] if product else None

        if not product:
            abort(404)

        related_items = dbs.execute(
            select(Product)
            .where(
                Product.is_active == 1,
                Product.id != product.id,
                Product.category == product.category,
            )
            .order_by(desc(Product.is_featured), Product.created_at.desc(), Product.name.asc())
            .limit(4)
        ).scalars().all()

    return render_template(
        "product_detail.html",
        title=f"{product.name} - Aung Market",
        product=product,
        related_items=related_items,
    )


# Cart routes
@app.post("/cart/add/<int:product_id>")
def cart_add(product_id: int):
    qty_raw = (request.form.get("quantity") or "1").strip()
    try:
        qty = int(qty_raw)
        if qty < 1 or qty > 50:
            raise ValueError
    except ValueError:
        flash("Quantity must be between 1 and 50.", "error")
        return redirect(url_for("menu"))

    with db() as dbs:
        row = dbs.execute(
            select(Product.id, Product.name, Product.price).where(
                Product.id == product_id,
                Product.is_active == 1,
            )
        ).one_or_none()

    if not row:
        flash("Product not found.", "error")
        return redirect(url_for("menu"))

    cart = cart_get()
    key = str(product_id)
    if key in cart:
        cart[key]["quantity"] = int(cart[key]["quantity"]) + qty
    else:
        cart[key] = {
            "product_id": row.id,
            "name": row.name,
            "price": float(row.price),
            "quantity": qty,
        }
    cart_save(cart)
    flash("Added to cart.", "success")
    return redirect(get_local_redirect("menu"))


@app.get("/cart")
def cart():
    cart = cart_get()
    total = cart_total(cart)
    return render_template(
        "cart.html",
        title="Cart - Aung Market",
        cart=list(cart.values()),
        total=total,
    )


@app.post("/cart/update")
def cart_update():
    cart = cart_get()
    # Form fields are posted as quantities[<product_id>].
    for key, item in list(cart.items()):
        q_raw = request.form.get(f"quantities[{item['product_id']}]", "")
        if q_raw == "":
            continue
        try:
            q = int(q_raw)
        except ValueError:
            q = item["quantity"]
        if q <= 0:
            cart.pop(key, None)
        else:
            cart[key]["quantity"] = min(q, 50)

    cart_save(cart)
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.post("/cart/remove/<int:product_id>")
def cart_remove(product_id: int):
    cart = cart_get()
    cart.pop(str(product_id), None)
    cart_save(cart)
    flash("Item removed.", "success")
    return redirect(url_for("cart"))


@app.post("/cart/clear")
def cart_clear():
    cart_save({})
    flash("Cart cleared.", "success")
    return redirect(url_for("cart"))


# Order routes
@app.get("/order/confirm")
def order_confirm():
    cart = cart_get()
    if not cart:
        flash("Cart is empty. Please add items first.", "error")
        return redirect(url_for("menu"))

    user = get_current_user()
    if user and (not user.phone.strip() or not user.address.strip()):
        flash("Please update phone and address in your profile before confirming order.", "error")
        return redirect(url_for("profile"))

    total = cart_total(cart)
    return render_template(
        "order_confirm.html",
        title="Confirm Order - Aung Market",
        cart=list(cart.values()),
        total=total,
        user_phone=user.phone if user else "",
        user_address=user.address if user else "",
    )


@app.post("/order/place")
def order_place():
    cart = cart_get()
    if not cart:
        flash("Cart is empty.", "error")
        return redirect(url_for("menu"))

    user = get_current_user()
    if user:
        with db() as dbs:
            db_user = dbs.get(User, user.id)
        if not db_user:
            flash("Please login again.", "error")
            return redirect(url_for("login"))
        customer_name = db_user.name
        phone = (db_user.phone or "").strip()
        address = (db_user.address or "").strip()
    else:
        customer_name = (request.form.get("customer_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()

    notes = (request.form.get("notes") or "").strip()

    if not customer_name or not phone or not address:
        flash("Customer name, phone, and address are required.", "error")
        return redirect(url_for("order_confirm"))

    total = cart_total(cart)
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db() as dbs:
        order = Order(
            user_id=user.id if user else None,
            customer_name=customer_name,
            phone=phone,
            address=address,
            notes=notes,
            status="Pending",
            total_amount=total,
            created_at=now_iso,
        )
        dbs.add(order)
        # Flush assigns `order.id` before inserting child order_items.
        dbs.flush()

        for item in cart.values():
            qty = int(item["quantity"])
            price = float(item["price"])
            line_total = qty * price
            dbs.add(
                OrderItem(
                    order_id=order.id,
                    item_name=item["name"],
                    quantity=qty,
                    unit_price=price,
                    line_total=line_total,
                )
            )

        dbs.commit()
        order_id = order.id

    cart_save({})
    flash("Order placed successfully.", "success")
    return redirect(url_for("order_receipt", order_id=order_id))


@app.get("/order/<int:order_id>/receipt")
def order_receipt(order_id: int):
    current = get_current_user()
    with db() as dbs:
        order = dbs.get(Order, order_id)
        if not order:
            abort(404)
        if current and (not current.is_admin) and order.user_id != current.id:
            abort(403)
        items = dbs.execute(
            select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id.asc())
        ).scalars().all()

    return render_template(
        "order_receipt.html",
        title="Receipt - Aung Market",
        order=order,
        items=items,
    )


@app.post("/feedback")
def feedback_store():
    order_id_raw = (request.form.get("order_id") or "").strip()

    redirect_url = url_for("home")
    if order_id_raw:
        try:
            order_id = int(order_id_raw)
            if order_id > 0:
                redirect_url = url_for("order_receipt", order_id=order_id)
        except ValueError:
            pass

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    message = (request.form.get("message") or "").strip()
    promotion = (request.form.get("promotion") or "").strip()

    if not all([name, email, phone, message]) or promotion not in {"Y", "N"}:
        flash("Please fill in all feedback fields.", "error")
        return redirect(redirect_url + "#feedback")

    sms = "Y" if request.form.get("sms") == "Y" else "N"
    whatsapp = "Y" if request.form.get("whatsapp") == "Y" else "N"
    emailch = "Y" if request.form.get("emailch") == "Y" else "N"

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db() as dbs:
        dbs.add(
            Feedback(
                name=name,
                email=email,
                phone=phone,
                message=message,
                promotion=promotion,
                channel_sms=sms,
                channel_whatsapp=whatsapp,
                channel_email=emailch,
                created_at=created_at,
            )
        )
        dbs.commit()

    flash("Thanks! Your feedback was sent.", "success")
    return redirect(redirect_url + "#feedback")


# Auth/role helpers
def require_login() -> CurrentUser:
    u = get_current_user()
    if not u:
        flash("Please login first.", "error")
        abort(redirect(url_for("login")))
    return u


def require_admin() -> CurrentUser:
    u = get_current_user()
    if not u or not u.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("home"))
    return u


# Authentication routes
@app.get("/login")
def login():
    return render_template("login.html", title="Login - Aung Market")


@app.post("/login")
def login_attempt():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    with db() as dbs:
        user = dbs.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()

    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    session["user_id"] = user.id
    flash("Logged in successfully.", "success")
    return redirect(url_for("home"))


@app.post("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out.", "success")
    return redirect(url_for("home"))


@app.get("/register")
def register():
    return render_template("register.html", title="Sign Up - Aung Market")


@app.post("/register")
def register_store():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password2 = request.form.get("password_confirmation") or ""

    if not name or not email or not password:
        flash("All fields are required.", "error")
        return redirect(url_for("register"))

    if password != password2:
        flash("Passwords do not match.", "error")
        return redirect(url_for("register"))

    with db() as dbs:
        try:
            dbs.add(
                User(
                    name=name,
                    email=email,
                    phone="",
                    address="",
                    password_hash=generate_password_hash(password),
                    is_admin=0,
                )
            )
            dbs.commit()
        except IntegrityError:
            dbs.rollback()
            flash("Email already registered.", "error")
            return redirect(url_for("register"))

    flash("Account created. Please login.", "success")
    return redirect(url_for("login"))


# Profile routes
@app.get("/profile")
def profile():
    u = get_current_user()
    if not u:
        flash("Please login first.", "error")
        return redirect(url_for("login"))
    return render_template("profile.html", title="My Profile - Aung Market", user=u)


@app.post("/profile/update")
def profile_update():
    u = get_current_user()
    if not u:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone") or "").strip()
    address = (request.form.get("address") or "").strip()
    if not name or not email or not phone or not address:
        flash("Name, email, phone, and address are required.", "error")
        return redirect(url_for("profile"))

    with db() as dbs:
        user = dbs.get(User, u.id)
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("login"))

        user.name = name
        user.email = email
        user.phone = phone
        user.address = address

        try:
            dbs.commit()
        except IntegrityError:
            dbs.rollback()
            flash("That email is already used.", "error")
            return redirect(url_for("profile"))

    flash("Profile updated.", "success")
    return redirect(url_for("profile"))


@app.get("/orders")
def my_orders():
    u = get_current_user()
    if not u:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    with db() as dbs:
        orders = dbs.execute(
            select(Order).where(Order.user_id == u.id).order_by(Order.id.desc()).limit(200)
        ).scalars().all()

    return render_template(
        "my_orders.html",
        title="My Orders - Aung Market",
        orders=orders,
    )


@app.post("/profile/password")
def profile_password_update():
    u = get_current_user()
    if not u:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("password") or ""
    confirm = request.form.get("password_confirmation") or ""

    if new_password != confirm:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile"))

    with db() as dbs:
        user = dbs.get(User, u.id)
        if not user or not check_password_hash(user.password_hash, current_password):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("profile"))

        user.password_hash = generate_password_hash(new_password)
        dbs.commit()

    flash("Password updated.", "success")
    return redirect(url_for("profile"))


# Admin routes
@app.get("/admin")
def admin_dashboard():
    u = get_current_user()
    if not u or not u.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("home"))

    # Feedback report date range uses date strings from query params (YYYY-MM-DD).
    from_d = (request.args.get("from") or "").strip()
    to_d = (request.args.get("to") or "").strip()

    if not from_d:
        from_d = datetime.now().strftime("%Y-%m-01")
    if not to_d:
        to_d = datetime.now().strftime("%Y-%m-%d")

    # Expand to full-day datetime boundaries for between filtering.
    start = f"{from_d} 00:00:00"
    end = f"{to_d} 23:59:59"

    with db() as dbs:
        menu_items = dbs.execute(select(Product).order_by(Product.id.desc())).scalars().all()
        feedback_rows = dbs.execute(
            select(Feedback)
            .where(Feedback.created_at.between(start, end))
            .order_by(Feedback.created_at.desc())
        ).scalars().all()
        orders = dbs.execute(
            select(Order)
            .where(Order.created_at.between(start, end))
            .order_by(Order.created_at.desc())
        ).scalars().all()

    summary = {
        "products": len(menu_items),
        "active_products": sum(1 for item in menu_items if int(item.is_active) == 1),
        "orders": len(orders),
        "revenue": sum(float(order.total_amount) for order in orders),
        "feedback": len(feedback_rows),
    }

    existing_categories = {m.category.strip() for m in menu_items if (m.category or "").strip()}
    category_options = sorted(set(DEFAULT_PRODUCT_CATEGORIES).union(existing_categories))

    return render_template(
        "admin_dashboard.html",
        title="Admin - Aung Market",
        from_=from_d,
        to=to_d,
        feedbackRows=feedback_rows,
        menuItems=menu_items,
        orders=orders,
        summary=summary,
        order_statuses=ORDER_STATUSES,
        category_options=category_options,
    )


@app.post("/admin/products")
def admin_product_store():
    u = get_current_user()
    if not u or not u.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("home"))

    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "").strip()
    description = (request.form.get("description") or "").strip()
    price_raw = (request.form.get("price") or "").strip()
    is_featured = 1 if request.form.get("is_featured") == "Y" else 0

    if not name or not category or not price_raw:
        flash("Name, category, and price are required.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        price = float(price_raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        flash("Price must be a number > 0.", "error")
        return redirect(url_for("admin_dashboard"))

    image_path = ""
    file = request.files.get("image_file")
    if file and file.filename:
        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            flash("Invalid image type.", "error")
            return redirect(url_for("admin_dashboard"))
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_name = f"{stamp}_{filename}"
        save_path = UPLOAD_DIR / final_name
        file.save(save_path)
        image_path = f"assets/images/menu_uploads/{final_name}"

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db() as dbs:
        dbs.add(
            Product(
                name=name,
                category=category,
                description=description,
                price=price,
                image_path=image_path,
                is_active=1,
                is_featured=is_featured,
                created_at=created_at,
            )
        )
        dbs.commit()

    flash("Accessory added.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/products/<int:product_id>/toggle")
def admin_product_toggle(product_id: int):
    u = get_current_user()
    if not u or not u.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("home"))

    with db() as dbs:
        product = dbs.get(Product, product_id)
        if not product:
            flash("Product not found.", "error")
            return redirect(url_for("admin_dashboard"))

        product.is_active = 0 if int(product.is_active) == 1 else 1
        dbs.commit()

    flash("Product status updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/products/<int:product_id>/delete")
def admin_product_delete(product_id: int):
    u = get_current_user()
    if not u or not u.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("home"))

    with db() as dbs:
        product = dbs.get(Product, product_id)
        if not product:
            flash("Product not found.", "error")
            return redirect(url_for("admin_dashboard"))

        # Best-effort delete uploaded image if in uploads folder
        img = product.image_path or ""
        if img.startswith("assets/images/menu_uploads/"):
            p = APP_DIR / "static" / img
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

        dbs.delete(product)
        dbs.commit()

    # also remove from cart if present
    cart = cart_get()
    cart.pop(str(product_id), None)
    cart_save(cart)

    flash("Product deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.get("/admin/orders/<int:order_id>")
def admin_order_detail(order_id: int):
    u = get_current_user()
    if not u or not u.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("home"))

    with db() as dbs:
        order = dbs.get(Order, order_id)
        if not order:
            flash("Order not found.", "error")
            return redirect(url_for("admin_dashboard"))

        items = dbs.execute(
            select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id.asc())
        ).scalars().all()

    return render_template(
        "admin_order_detail.html",
        title=f"Order #{order_id} - Admin",
        order=order,
        items=items,
        order_statuses=ORDER_STATUSES,
    )


@app.post("/admin/orders/<int:order_id>/status")
def admin_order_status_update(order_id: int):
    u = get_current_user()
    if not u or not u.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("home"))

    next_url = (request.form.get("next") or "").strip()
    if not next_url.startswith("/"):
        next_url = url_for("admin_dashboard")

    new_status = (request.form.get("status") or "").strip()
    if new_status not in ORDER_STATUSES:
        flash("Invalid order status.", "error")
        return redirect(next_url)

    with db() as dbs:
        order = dbs.get(Order, order_id)
        if not order:
            flash("Order not found.", "error")
            return redirect(next_url)

        order.status = new_status
        dbs.commit()

    flash(f"Order #{order_id} status updated to {new_status}.", "success")
    return redirect(next_url)
# Admin: delete order history

@app.post("/admin/orders/<int:order_id>/delete")
def admin_order_delete(order_id: int):
    u = get_current_user()
    if not u or not u.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("home"))

    with db() as dbs:
        order = dbs.get(Order, order_id)
        if not order:
            flash("Order not found.", "error")
            return redirect(url_for("admin_dashboard"))

        items = dbs.execute(
            select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id.asc())
        ).scalars().all()
        for item in items:
            dbs.delete(item)

        dbs.delete(order)
        dbs.commit()

    flash(f"Order #{order_id} deleted.", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
