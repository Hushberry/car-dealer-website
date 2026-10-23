# PrimeDrive Motors

A luxury car dealership website with a full admin panel, built with **Flask** and **SQLite**. Customers can browse cars for sale and rent, request to sell or swap their car, read and submit reviews, and contact the showroom. The owner manages everything from a private dashboard.

**Live demo:** https://hushberry.pythonanywhere.com

![Homepage](docs/screenshots/home.png)

## Features

**For customers**
- Luxury homepage with latest arrivals showcase, services, about and gallery
- Cars page with search, filters and sorting
- Car detail pages with photo carousel
- Sell and Swap request forms
- Contact page with private viewing booking and WhatsApp link
- Customer reviews with optional photo, approved by the owner before publishing
- Light and dark theme
- Fully responsive, built for mobile first

**For the dealer (admin panel)**
- Add, edit and delete cars with multiple photos
- Mark cars as sold, set sale, rent or auction listings
- Manage sell and swap requests, contact messages and auctions
- Approve or reject customer reviews
- Email alerts for new enquiries
- Admin login with attempt limiting

![Cars page](docs/screenshots/cars.png)
![Admin dashboard](docs/screenshots/admin.png)

## Tech stack

Python, Flask, Flask-WTF (CSRF protection), SQLite, Jinja2, vanilla JavaScript, custom CSS (no framework), Pillow for image handling.

## Security

CSRF protection on all forms, honeypot and per-IP rate limits on public forms, login attempt limiting, validated and resized image uploads, secrets kept in environment variables.

## Run locally

```bash
git clone https://github.com/Hushberry/car-dealer-website.git
cd car-dealer-website
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # then fill in your own values
python app.py
```

## Configuration

Settings live in a `.env` file that is never committed. See `.env.example` for the names:
`SECRET_KEY`, `RECOVERY_KEY`, `BRAND_NAME`, `SMTP_USER`, `SMTP_PASS`, `ALERT_EMAIL_TO`, `REVIEWS_AUTO_APPROVE`, `CONTACT_EMAIL`, `SHOWROOM_HOURS`.

## Author

Built by Vincent — [github.com/Hushberry](https://github.com/Hushberry)
