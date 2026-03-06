Aung Market (Flask + Ssqlalchemy) 

Features
- Home page shows featured accessories
- Take Order page: accessories grouped by category
- Cart: update/remove/clear
- Confirm Order -> Place Order -> Receipt
- Login / Sign Up / Logout
- Profile edit + change password
- Admin panel:
  - Add accessory (with optional image upload)
  - Hide/Restore product
  - Delete product
  - Feedback report (date range)
  - Order history + order detail

Run
1) Create venv and install
   pip install -r requirements.txt
2) Start
   python app.py
3) Open
   http://127.0.0.1:5000

Admin Demo Account (auto-created)
- Email: admin@aungmarket.test
- Password: admin123

Notes
- Uploaded images are saved to: static/assets/images/menu_uploads/
- Database file: aung_market.db (auto-created on first run)
