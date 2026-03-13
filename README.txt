Aung Market

Overview
- Aung Market is a Flask-based luxury accessories ordering system.
- It uses SQLAlchemy with SQLite for data storage.
- It uses Flask-WTF forms for customer and admin input handling.

Current Features
- Home page with featured accessories
- Take Order page with all active items shown in card layout
- Shopping cart with add, update, remove, and clear actions
- Order confirmation, receipt, and feedback flow
- Customer login, registration, logout
- Customer profile update for name, email, phone, and address
- Customer password change
- Customer read-only order history
- Admin dashboard for product management
- Admin can:
  - add accessories
  - choose category from a dropdown
  - mark items as featured or non-featured
  - hide or restore products
  - filter order history by from/to date
  - update order status
  - view feedback report
- Favicon support for browser tab icon

Order Rules
- Featured items appear on the home page.
- All items appear in Take Order.
- Logged-in customers use their saved profile details during checkout.
- Guests can still place orders by entering their details manually.
- Order email, phone, and address are stored with the order.

Tech Stack
- Flask 3
- SQLAlchemy 2
- Flask-WTF
- SQLite
- Werkzeug

Project Structure
- `app.py`
  Main Flask routes and application logic.
- `database.py`
  SQLAlchemy engine, session, models, and database initialization.
- `forms.py`
  Flask-WTF forms used by login, register, profile, order, feedback, and admin pages.
- `templates/`
  HTML templates for customer and admin pages.
- `static/`
  CSS, images, uploads, and favicon.
- `aung_market.db`
  SQLite database file created locally.

Database Models
- `User`
- `Product`
- `Feedback`
- `Order`
- `OrderItem`

Default Product Categories
- Watches
- Jewelry
- Bags
- Sunglasses
- Perfume

Order Status Values
- Pending
- Confirmed
- Preparing
- Out for Delivery
- Completed
- Cancelled

How To Run
1. Open terminal in `C:\Documents\aung_market`
2. Create and activate a virtual environment if needed
3. Install dependencies

   pip install -r requirements.txt

4. Start the app

   python app.py

5. Open in browser

   http://127.0.0.1:5000

Requirements
- Python 3.10+ recommended
- Packages are listed in `requirements.txt`

Database Notes
- The app creates the SQLite database automatically on first run.
- Lightweight schema updates are handled in `init_db()` inside `database.py`.
- Uploaded product images are stored in:

  `static/assets/images/menu_uploads/`

Default Admin Account
- Email: `admin@gmail.com`
- Password: `admin123`

Important Notes
- Admin delete functions were removed from the admin side.
- Product visibility is controlled by hide/restore, not delete.
- CSRF protection is enabled for POST forms.
- Home page feedback form was moved to the order receipt page.

Main Customer Pages
- `/`
- `/menu`
- `/cart`
- `/order/confirm`
- `/login`
- `/register`
- `/profile`
- `/orders`

Main Admin Pages
- `/admin`
- `/admin/orders/<order_id>`

Future Improvements
- Add migrations with Alembic
- Split routes into Flask blueprints
- Add automated UI tests
- Add email notification after order placement
