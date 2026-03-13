# Aung Market

Flask e-commerce project for browsing accessories, placing orders, and managing products through an admin dashboard.

## Features

- Product catalog with search, category filter, and sorting
- Product detail page with related items
- Cart, checkout, receipt, and feedback flow
- Customer login, registration, profile update, and order history
- Admin dashboard with summary cards for products, orders, revenue, and feedback
- Admin product management with featured and visibility controls
- Order status tracking for customer and admin pages
- Responsive layout for storefront and dashboard screens

## Tech Stack

- Python 3
- Flask
- SQLAlchemy
- Flask-WTF
- SQLite
- HTML, Jinja, CSS

## Project Structure

- `app.py` - routes and request handling
- `database.py` - models, database setup, and seed data
- `forms.py` - Flask-WTF forms
- `templates/` - storefront and admin templates
- `static/` - CSS, images, and uploaded files

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

4. Open `http://127.0.0.1:5000`

## Default Admin Account

- Email: `admin@gmail.com`
- Password: `admin123`

## Main Routes

- `/` home page
- `/menu` product catalog
- `/products/<id>` product detail page
- `/cart` shopping cart
- `/order/confirm` checkout page
- `/orders` customer order history
- `/admin` admin dashboard

## Notes

- The SQLite database is created locally by the app.
- Uploaded product images are stored under `static/assets/images/menu_uploads/`.
- Product removal is handled with hide and restore actions rather than hard delete.

## Verification

- Python syntax checked with `py_compile`
- Key routes tested locally with the Flask test client
