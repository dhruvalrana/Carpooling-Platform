# ARCHITECTURE.md — Enterprise Carpooling Platform

## 1. Stack Summary

| Layer | Choice | Why |
|---|---|---|
| Backend framework | Django 5.x | Explicit requirement; batteries-included admin/auth/ORM. |
| API layer | Django REST Framework | Powers AJAX search, booking, wallet, and feeds the WebSocket/polling client for tracking. |
| Real-time | Django Channels + Redis (channel layer) | Needed for live location push and in-trip chat. Fallback: short-interval polling (5s) via DRF if Channels setup risks the timeline. |
| Async tasks | Celery + Redis (broker) | Report aggregation, notification dispatch, wallet reconciliation — keep off the request/response path. |
| Database | PostgreSQL | Row-level constraints, JSONField where useful (e.g., route geometry cache), good with GIS if needed later. |
| Frontend | Django templates + vanilla JS/htmx + Bootstrap 5 or Tailwind (see design.md) | "Website," not SPA — keep templates server-rendered; use htmx or small JS modules for the interactive bits (search results, chat, map). |
| Maps/routing | Leaflet.js + OpenStreetMap tiles + OSRM (or Google Maps JS API if a key is available) | See ADR-1 below. |
| Payments | Razorpay Test Mode (Checkout.js + server-side order/verify) | Explicit requirement. |
| Auth | Django session auth (server) | Simpler than JWT for a template-driven site; DRF views reuse the same session. |
| Deployment | Single Docker Compose stack: `web` (Django/Gunicorn), `worker` (Celery), `redis`, `postgres`, optionally `daphne`/`uvicorn` for ASGI if Channels is used | Fast to spin up for a hackathon judge/demo. |

### ADR-1: Map Provider
- **Recommendation: Leaflet + OSRM (self-hosted or public demo server) or Mapbox free tier.**
- Reasoning: no billing account needed mid-hackathon, no risk of hitting a Google Maps quota/key issue during judging. Trade-off: slightly rougher UI polish and geocoding is weaker — mitigate with Nominatim for geocoding.
- If the team already has a Google Maps API key with billing enabled, it's an acceptable swap — the mapping calls should be isolated behind a single `services/maps.py` interface so the provider can change without touching views.

### ADR-2: Real-time Transport
- **Recommendation: Start with polling (DRF endpoint, 3–5s interval) for live tracking in Phase 1 of that module; upgrade to Django Channels + WebSocket only once the core flow works end-to-end.**
- Reasoning: Channels/ASGI misconfiguration is the single most common thing that silently breaks a Django hackathon demo an hour before judging. Ship the boring version first, then upgrade.
- Chat can follow the same pattern: polling first, WebSocket upgrade second.

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (Employee)                    │
│  Django templates + htmx/JS   |   Leaflet map   |   Chat UI  │
└───────────────┬───────────────────────────┬──────────────────┘
                │ HTTP (templates, forms)    │ REST/WS (search, book,
                │                            │ location ping, chat)
                ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Django (Gunicorn/ASGI)                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐ │
│  │  views/    │ │   api/     │ │ consumers/ │ │  services/   │ │
│  │ (templates)│ │ (DRF)      │ │ (Channels) │ │ (maps, pay,  │ │
│  │            │ │            │ │            │ │  matching)   │ │
│  └───────────┘ └───────────┘ └───────────┘ └──────────────┘ │
└───────────┬───────────────┬───────────────┬──────────────────┘
            │               │               │
            ▼               ▼               ▼
      ┌──────────┐   ┌────────────┐   ┌──────────┐
      │PostgreSQL│   │   Redis    │   │  Celery  │
      │          │   │(channels + │   │ workers  │
      │          │   │ celery)    │   │          │
      └──────────┘   └────────────┘   └──────────┘
                                             │
                             ┌───────────────┴───────────────┐
                             ▼                                ▼
                     Razorpay Test API                 Maps/Routing API
```

## 3. Django App Breakdown

One app per bounded context. Keep apps independently testable; cross-app calls go through explicit service functions, not direct model reach-through where avoidable.

```
carpool_project/
├── core/            # shared base models (TimeStamped, OrgScoped mixins), permissions, exceptions
├── organizations/    # Organization, OrgSettings, Admin-employee linkage
├── accounts/         # CustomUser, Profile, auth views, role checks
├── vehicles/         # Vehicle model + CRUD
├── rides/            # Ride (offer), RideSearch, matching logic, RouteConfirmation
├── trips/            # Trip (booking), TripStatus state machine, TripParticipant
├── tracking/         # LocationPing model, Channels consumer, ETA calc
├── chat/             # Message model, Channels consumer (or polling endpoint)
├── payments/         # Payment, Razorpay integration, webhook handling
├── wallet/           # Wallet, WalletTransaction
├── reports/          # aggregation queries/services, Celery tasks
├── notifications/    # in-app Notification model, dispatch service
└── services/         # cross-cutting: maps.py, matching.py, cost_calc.py
```

Guidance: `rides` is "supply" (offer + search), `trips` is "the actual booked instance." Don't merge them — a `Ride` can have multiple `Trip` bookings up to seat capacity.

## 4. Core Data Model (entities, not full field list — refine in Phase 1)

```
Organization
  id, name, domain, settings (fk OrgSettings)

OrgSettings
  organization (fk, 1:1), fuel_cost_per_km, currency, max_search_radius_km,
  booking_cutoff_minutes

User (extends AbstractUser)
  organization (fk), role [ADMIN|EMPLOYEE], phone, photo, is_active_on_platform

Vehicle
  owner (fk User), model, registration_number, seating_capacity

Ride                                   # the published offer
  driver (fk User), vehicle (fk Vehicle),
  pickup_location (lat/lng + label), destination (lat/lng + label),
  departure_datetime, seats_total, seats_available, fare_per_seat,
  is_recurring, recurrence_rule (nullable), route_geometry (cached),
  status [ACTIVE|FULL|CANCELLED|EXPIRED]

Trip                                   # one booking = one passenger on one ride
  ride (fk Ride), passenger (fk User), seats_booked,
  status [BOOKED|STARTED|IN_PROGRESS|COMPLETED|PAYMENT_PENDING|PAYMENT_COMPLETED|CANCELLED],
  fare_amount, started_at, completed_at

LocationPing
  ride (fk Ride), lat, lng, heading, speed, recorded_at    # driver-originated

Message
  trip (fk Trip), sender (fk User), body, sent_at

Wallet
  user (fk User, 1:1), balance

WalletTransaction
  wallet (fk Wallet), amount, type [CREDIT|DEBIT], reason, related_trip (fk Trip, nullable), created_at

Payment
  trip (fk Trip), method [CASH|CARD|UPI|WALLET], amount, status [PENDING|SUCCESS|FAILED],
  razorpay_order_id, razorpay_payment_id, created_at

SavedPlace
  user (fk User), label, lat, lng

Notification
  user (fk User), type, payload (json), read_at (nullable), created_at
```

Notes:
- `Ride.seats_available` should be decremented transactionally (`select_for_update`) on booking to avoid overbooking races — this is the one place a naive implementation will break under concurrent judging traffic.
- Every model that isn't already reachable via `organization` should still be filterable by org through its `driver`/`owner`/`user` FK — write a shared queryset mixin (`OrgScopedQuerySet`) rather than repeating `.filter(...organization=...)` everywhere.

## 5. Trip Status State Machine

```
BOOKED ──(driver starts ride)──► STARTED ──► IN_PROGRESS ──(driver ends ride)──► COMPLETED
                                                                                    │
                                                                                    ▼
                                                                            PAYMENT_PENDING
                                                                                    │
                                                                          (payment success)
                                                                                    ▼
                                                                          PAYMENT_COMPLETED

BOOKED ──(cancel, bonus feature)──► CANCELLED
```

Implement as an explicit `TRANSITIONS` dict in `trips/services.py` with a single `transition(trip, new_status, actor)` function that validates the edge and raises on illegal transitions — don't let views set `trip.status = X` directly.

## 6. Real-Time Tracking Design

1. Driver's browser, once trip status = `STARTED`, begins sending `navigator.geolocation.watchPosition` pings to `POST /api/tracking/ping/` (or a WS message) every ~5s.
2. Server stores the latest ping (and optionally a trail) on `LocationPing`, keyed by `ride`.
3. Passenger's browser polls `GET /api/tracking/<ride_id>/latest/` every 3–5s (Phase 1) or subscribes to a Channels group `tracking_<ride_id>` (Phase 2 upgrade).
4. ETA: call the routing service (OSRM `/route` or Google Directions) with current position → destination; cache for ~15s to avoid hammering the routing API.
5. Tracking access control: only the driver and booked passengers of that specific `ride` may read/write pings — enforce in the view/consumer, not just by "security through obscurity" of the ride ID.
6. Stop accepting/broadcasting pings once trip status leaves `IN_PROGRESS`.

## 7. Payments Flow

1. Trip reaches `COMPLETED` → status auto-moves to `PAYMENT_PENDING`.
2. Passenger chooses method:
   - **Cash**: driver marks "cash received" → `Payment.status = SUCCESS` directly (no gateway).
   - **Wallet**: server checks `Wallet.balance >= fare_amount`, debits atomically, creates `WalletTransaction`, marks `Payment.status = SUCCESS`.
   - **Card/UPI**: create a Razorpay Order server-side → return `order_id` to client → Razorpay Checkout.js collects payment → client posts the Razorpay payment/signature back → server verifies signature server-side (never trust client-reported success) → mark `Payment.status = SUCCESS`.
3. On `Payment.status = SUCCESS`, transition `Trip.status = PAYMENT_COMPLETED`.
4. Wallet recharge follows the same Razorpay Order → Checkout → verify pattern, crediting `Wallet.balance` on verified success.

## 8. Matching / Search Logic (MVP, not ML)

For "Find a Ride": given search pickup/destination/date/time/seats —
1. Filter `Ride` where `status=ACTIVE`, `departure_datetime` within a configurable window of the requested time, `seats_available >= requested_seats`, same `organization`.
2. Filter by geographic proximity: pickup within `OrgSettings.max_search_radius_km` of ride's pickup, same rough bearing toward destination (simple haversine distance check is enough — don't build a routing-overlap algorithm for MVP).
3. Sort by (time proximity, distance proximity, fare).
4. "Intelligent Ride Matching" (route-overlap scoring) is explicitly a bonus feature — don't build it before the mandatory list is done.

## 9. API Surface (representative, not exhaustive — finalize per phase)

```
POST   /api/auth/signup/
POST   /api/auth/login/
GET    /api/rides/search/?pickup=&destination=&date=&time=&seats=
POST   /api/rides/                      # publish a ride
POST   /api/rides/<id>/route-preview/   # route confirmation step
POST   /api/trips/                      # book a ride -> creates Trip
GET    /api/trips/mine/
POST   /api/trips/<id>/start/
POST   /api/trips/<id>/complete/
POST   /api/tracking/ping/
GET    /api/tracking/<ride_id>/latest/
GET    /api/chat/<trip_id>/messages/
POST   /api/chat/<trip_id>/messages/
POST   /api/payments/<trip_id>/create-order/
POST   /api/payments/<trip_id>/verify/
POST   /api/wallet/recharge/create-order/
POST   /api/wallet/recharge/verify/
GET    /api/reports/summary/
GET    /api/reports/org-summary/        # admin only
```

## 10. Security & Multi-Tenancy Enforcement

- Every DRF viewset/queryset starts from `self.request.user.organization` — never a global `Model.objects.all()` in a view touching org-scoped data.
- Role checks via a small `IsOrgAdmin` / `IsEmployee` DRF permission class, applied per-viewset — not scattered `if request.user.role == "ADMIN"` checks in template logic only.
- CSRF protection stays on for template form posts; DRF endpoints called from the same-origin JS use the standard Django CSRF cookie/header pattern.
- Razorpay webhook/verify endpoints validate signatures server-side; never trust a client-supplied "payment succeeded" flag alone.
- Location data is only ever exposed to the two (or more) participants of that specific trip.

## 11. Deployment (hackathon-scope)

```
docker-compose.yml
  services:
    web        (Django, Gunicorn or Daphne/Uvicorn if Channels used)
    worker     (Celery)
    redis
    postgres
```
- `.env` for secrets (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `MAPS_API_KEY` if applicable, `DJANGO_SECRET_KEY`, `DATABASE_URL`).
- `python manage.py seed_demo_data` management command to pre-populate 1–2 orgs, several employees, vehicles, and a couple of rides — critical for a fast, reliable live demo.

## 12. What NOT to build (explicitly out of architecture scope)

- Kubernetes/multi-node deploy.
- Custom WebRTC signaling server for voice call — if the team wants a real call, use a hosted embed (e.g., a third-party click-to-call widget) or fake it with a "Call" `tel:` link deep-linking to the phone's dialer; don't build a signaling server under hackathon time pressure.
- A generalized route-optimization/VRP solver — this is bonus scope only.
