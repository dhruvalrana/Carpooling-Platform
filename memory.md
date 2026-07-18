# CarpoolOrg - Project Memory

> Living document. Update whenever a bug is fixed, a decision is made, or a new feature is added.

---

## Project Overview

| Field | Value |
|---|---|
| Project Name | CarpoolOrg |
| Type | Enterprise Carpooling / Ride-sharing Platform |
| Stack | Django 5.2, SQLite (dev) / PostgreSQL (prod), Leaflet.js + OpenStreetMap, Razorpay |
| Root Directory | `d:\Odoo X KSV\KSV\` |
| Settings Module | `carpool_project.settings.dev` |
| ASGI | Daphne + Django Channels (InMemoryChannelLayer in dev) |

---

## Demo Credentials

| Role | Email | Password |
|---|---|---|
| Org Admin | admin@demo.com | demo1234 |
| Driver | driver@demo.com | demo1234 |
| Passenger | passenger@demo.com | demo1234 |

- Org domain: `demo.com`
- Passenger wallet pre-loaded with Rs.500
- Demo vehicle: Maruti Swift - MH12AB1234 (owned by driver)
- Demo ride: Andheri Station -> BKC, Mumbai

Seed command:
```
python manage.py seed_demo_data
```

---

## How to Run

```bash
cd "d:\Odoo X KSV\KSV"
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver 8000
```

Open: http://127.0.0.1:8000

---

## App Structure

| App | Purpose |
|---|---|
| `core` | TimeStampedModel, custom exceptions, seed_demo_data management command |
| `organizations` | Organization, OrgSettings - domain allow-list onboarding |
| `accounts` | Custom User (AbstractUser + org + role + phone) |
| `vehicles` | Vehicle - CRUD for driver-owned vehicles |
| `rides` | Ride - the published offer; geocoding + OSRM route preview |
| `trips` | Trip (booking), Message (in-trip chat); strict state machine |
| `tracking` | LocationPing - driver GPS pings + polling API for passengers |
| `payments` | Payment, Razorpay order creation + HMAC verification |
| `wallet` | Wallet, WalletTransaction - balance + transaction history |
| `reports` | No models; computed aggregations from other apps |
| `notifications` | Notification - in-app dispatcher |
| `chat` | Stub - messages stored in trips.Message |

---

## Key Models

### accounts.User
- Extends AbstractUser
- Fields: organization, role (ADMIN/EMPLOYEE), phone, photo, emergency_contact
- username = email (required for AuthenticationForm compatibility)

### rides.Ride
- Statuses: ACTIVE, FULL, CANCELLED, EXPIRED
- route_geometry - JSONField caching OSRM polyline

### trips.Trip
- Statuses: BOOKED -> STARTED -> IN_PROGRESS -> COMPLETED -> PAYMENT_PENDING -> PAYMENT_COMPLETED
- State machine enforced in trips/services.py with select_for_update()

### wallet.Wallet
- balance DecimalField
- Related WalletTransaction (CREDIT / DEBIT)

### payments.Payment
- Razorpay order_id, payment_id, signature stored
- HMAC verified server-side (payments/services.py::verify_razorpay_signature)

---

## Bugs Fixed

### [CRITICAL] Login never succeeded
- **File:** `accounts/views.py` line 22
- **Root cause:** AuthenticationForm requires `request` as its FIRST positional argument.
  It was missing, so authenticate() was never called and form.is_valid() silently returned False.
- **Fix:**
  ```diff
  - form = LoginForm(data=request.POST or None)
  + form = LoginForm(request, data=request.POST or None)
  ```
- **Date fixed:** 2026-07-18

### [MINOR] Unicode arrows and checkmarks crashed Windows terminal (cp1252)
- **Files:** seed_demo_data.py, rides/models.py, vehicles/models.py
- **Fix:** Replaced Unicode em-dashes and arrows with ASCII equivalents (->, -)

---

## Settings Notes

### base.py
- AUTH_USER_MODEL = 'accounts.User'
- TIME_ZONE = 'Asia/Kolkata'
- RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET read from .env

### dev.py
- SESSION_COOKIE_SECURE = False   (allows sessions over plain HTTP)
- CSRF_COOKIE_SECURE = False      (allows CSRF over plain HTTP)
- CORS_ALLOW_ALL_ORIGINS = True
- Database: SQLite at db.sqlite3

### .env (do not commit secrets)
```
DEBUG=True
SECRET_KEY=django-insecure-carpool-dev-key-change-in-production-!!
DATABASE_URL=sqlite:///db.sqlite3
RAZORPAY_KEY_ID=rzp_test_placeholder
RAZORPAY_KEY_SECRET=placeholder_secret
```

---

## URL Map

| URL | Name |
|---|---|
| / | splash |
| /login/ | login |
| /signup/ | signup |
| /logout/ | logout |
| /dashboard/ | dashboard |
| /dashboard/employee/ | employee_dashboard |
| /dashboard/admin/ | admin_dashboard |
| /profile/ | profile |
| /vehicles/ | my_vehicles |
| /vehicles/add/ | add_vehicle |
| /vehicles/\<pk\>/edit/ | edit_vehicle |
| /vehicles/\<pk\>/delete/ | delete_vehicle |
| /rides/offer/ | offer_ride |
| /rides/offer/confirm/ | route_confirm_offer |
| /rides/find/ | find_ride |
| /rides/\<pk\>/ | ride_detail |
| /rides/mine/ | my_offered_rides |
| /trips/ | my_trips |
| /trips/\<pk\>/ | trip_detail |
| /trips/\<pk\>/transition/ | transition_trip |
| /trips/\<pk\>/chat/ | trip_chat |
| /trips/history/ | ride_history |
| /payments/\<pk\>/ | payment_screen |
| /payments/\<pk\>/process/ | process_payment |
| /payments/\<pk\>/verify/ | verify_payment |
| /wallet/ | wallet |
| /wallet/recharge/ | wallet_recharge |
| /reports/ | reports |
| /reports/org/ | org_reports |
| /notifications/ | notifications |
| /admin/ | Django admin |

---

## External Services

| Service | Usage | Notes |
|---|---|---|
| Nominatim (OSM) | Geocoding address to lat/lng | rides/services.py::geocode() - no API key |
| OSRM | Route geometry and distance | rides/services.py::get_route_preview() - public demo |
| Razorpay | Payments (test mode) | RAZORPAY_KEY_ID / SECRET in .env |
| Leaflet.js | Map rendering in browser | Loaded via CDN in base.html |

---

## Templates Inventory

```
templates/
  base.html                     Shell: navbar, sidebar, flash messages
  accounts/
    splash.html                 Landing page (unauthenticated)
    login.html                  Login form
    signup.html                 Signup form (org auto-detected by email domain)
    employee_dashboard.html     Employee home with quick stats
    admin_dashboard.html        Admin home with org stats
    profile.html                Profile edit
  vehicles/
    my_vehicles.html            Vehicle card grid + empty state
    vehicle_form.html           Add / Edit vehicle
  rides/
    offer_ride.html             Offer a ride multi-section form
    route_confirm.html          Route preview + Leaflet map + publish
    find_ride.html              Search form + results list + route map
    ride_detail.html            Ride info + booking form + Leaflet map
    my_offered_rides.html       Driver's published rides list
  trips/
    my_trips.html               Tabbed trip list (upcoming/active/completed)
    trip_detail.html            Trip stepper + live GPS + chat + payment CTA
    ride_history.html           Completed trips table / mobile cards
  payments/
    payment.html                Payment method selection (Cash/Wallet/Card/UPI)
    razorpay_checkout.html      Razorpay Checkout.js integration
  wallet/
    wallet.html                 Balance card + recharge + transaction history
  reports/
    personal.html               Personal stat cards + recent trips table
    org.html                    Org-level stats (admin only)
    settings.html               Settings hub
  notifications/
    list.html                   Notification list
```

---

## Design Tokens (static/css/main.css)

| Token | Value | Use |
|---|---|---|
| --transit-blue | #2B3A67 | Primary brand colour |
| --route-amber | #E8A33D | Route lines, CTAs, fare amounts |
| --eco-teal | #2E8B74 | Eco stats, credit amounts |
| --alert-rust | #C0392B | Errors, debit amounts |
| --font-display | Space Grotesk | Headings |
| --font-body | Inter | Body text |
| --font-mono | JetBrains Mono | Numbers, IDs, codes |

Key CSS components:
- `.ride-card` - ride list card with route-line
- `.route-line-vertical` / `.route-dot-sm` - signature route line element
- `.trip-stepper` - status progress bar
- `.chat-panel` / `.chat-msg.me` / `.chat-msg.them` - in-trip chat
- `.payment-card` - large tappable payment method card
- `.stat-card` - KPI card on dashboards
- `.badge` - status pill (badge-booked, badge-active, etc.)
- `.empty-state` - empty content placeholder with route line graphic

---

## Requirements

```
Django==5.2.13
djangorestframework==3.14.0
django-environ==0.11.2
channels==4.3.2
channels-redis==4.3.0
celery==5.3.4
redis==5.0.1
psycopg2-binary==2.9.11
Pillow==11.2.1
django-cors-headers==4.3.0
razorpay==1.3.0
whitenoise==6.6.0
requests==2.32.5
daphne==4.1.2
```

Note: A urllib3 version warning appears in the console - it is harmless and does not affect functionality.

---

## Coding Conventions (from rules.md)

1. Business logic lives in services.py - views only call service functions
2. State machine in trips/services.py - all Trip status changes go through transition()
3. Org isolation - all queries filter by request.user.organization
4. Atomic financial ops - wallet debit and seat decrement use select_for_update() inside transaction.atomic()
5. No client-trusted payment - Razorpay HMAC verified server-side before marking trip paid
6. Mobile-first - all layouts responsive to 360px+ width

---

## Live Tracking Flow

```
Driver (browser):
  navigator.geolocation.watchPosition()
  -> POST /api/tracking/ping/ { ride_id, lat, lng, heading, speed }
  -> LocationPing.objects.create(...)

Passenger (browser):
  setInterval(4000ms)
  -> GET /api/tracking/<ride_id>/latest/
  <- { lat, lng, heading, speed }
  -> L.marker.setLatLng(ll)   (Leaflet map updates)
```

---

## Chat Flow

```
Send message:
  POST /trips/<pk>/chat/   body=<text>
  -> Message.objects.create(trip, sender, body)
  <- { id, body, sender_name, sent_at }

Poll new messages:
  GET /api/chat/<trip_id>/messages/?after=<last_id>
  <- { results: [{ id, body, sender_name }] }
  -> append new messages to .chat-panel DOM
```

---

## Migrations Status (as of 2026-07-18)

All initial migrations applied successfully:
- organizations 0001_initial
- accounts 0001_initial
- notifications 0001_initial
- vehicles 0001_initial
- rides 0001_initial
- tracking 0001_initial
- trips 0001_initial (Trip + Message)
- wallet 0001_initial (Wallet + WalletTransaction)
- payments 0001_initial

---

*Last updated: 2026-07-18*
