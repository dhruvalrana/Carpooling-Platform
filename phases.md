# PHASES.md — Build Roadmap

Sequenced so that at the end of every phase, the app is runnable and demoable in its current partial state — never leave it broken between phases. Time estimates assume a hackathon-style compressed timeline; adjust to the actual clock the team has, but keep the order.

## Phase 0 — Project Setup & Decisions
**Goal:** empty-but-running Django project with the real architecture in place, and the open questions from `prd.md` §10 resolved.

- Resolve `prd.md` §10 open questions (org onboarding mechanism, driver-approval-or-instant-booking, map provider, voice-call approach, recurrence scope).
- `django-admin startproject`, Docker Compose (`web`, `postgres`, `redis`, `worker`), `.env` handling.
- Create all apps listed in `architecture.md` §3 (even if mostly empty) and register them.
- Custom `accounts.User` model with `role` and `organization` fields, set as `AUTH_USER_MODEL` **before any migration runs**.
- Base mixins: `TimeStampedModel`, `OrgScopedModel`/`OrgScopedQuerySet`.
- CI-lite: a pre-commit hook or simple script running `manage.py test` + linter (black/ruff) before commit.
- Seed-data management command skeleton (`seed_demo_data`) — fill it in as models land.

**Exit criteria:** `docker-compose up` runs, `/admin/` loads, empty apps are registered, decisions from §10 are written back into `prd.md`.

## Phase 1 — Auth, Organizations, Profiles
**Goal:** an employee can sign up under an org, log in, and see a dashboard; an admin can log in and see an admin dashboard.

- `Organization`, `OrgSettings` models + admin registration.
- Signup flow per the chosen onboarding mechanism from Phase 0.
- Login/logout, profile creation/edit screens.
- Role-based redirect: Admin → admin dashboard, Employee → employee dashboard.
- `IsOrgAdmin` / `IsEmployee` permission classes (used from here on for every subsequent API).
- Splash/Login/Sign Up/Profile templates per `design.md`.

**Exit criteria:** two distinct demo users (one admin, one employee) can be created and logged in through the real UI, correctly redirected by role.

## Phase 2 — Vehicle Management
**Goal:** employees can register/manage vehicles; this becomes the gate for Phase 3.

- `Vehicle` model, CRUD views/templates, "My Vehicle" screen.
- Enforce: an employee must have ≥1 vehicle before they can publish a ride (checked in Phase 3, built here).

**Exit criteria:** an employee can add a vehicle and see it listed; empty state clearly prompts adding one.

## Phase 3 — Offer a Ride / Find a Ride (core marketplace)
**Goal:** the heart of the product — publishing and discovering rides.

- `Ride` model + publish flow (pickup/destination/date-time/seats/fare) with route-confirmation step (map integration begins here — see `architecture.md` ADR-1).
- Search flow: search form → route confirmation → matching results (matching logic per `architecture.md` §8).
- Geocoding for free-text pickup/destination → lat/lng (Nominatim or Google Geocoding, per Phase 0 decision).

**Exit criteria:** employee A publishes a ride; employee B searches and sees it in results with correct fare/seats/route.

## Phase 4 — Booking & Trip Management
**Goal:** a searched ride becomes a real booked `Trip`, with the full status lifecycle and in-trip chat.

- `Trip` model, booking service with `select_for_update()` seat-lock (per `rules.md` §6).
- "My Trips" list + detail (driver view vs. passenger view).
- Trip status transitions: `BOOKED → STARTED → IN_PROGRESS → COMPLETED` (payment states land in Phase 6).
- Chat: `Message` model + polling endpoint first (per `architecture.md` ADR-2); UI panel in trip detail.
- Voice call: per Phase 0 decision (`tel:` deep-link is the safe default).

**Exit criteria:** employee B books employee A's ride; both see it in My Trips; driver can move it through `STARTED`/`IN_PROGRESS`/`COMPLETED`; both can exchange chat messages.

## Phase 5 — Live Trip Tracking
**Goal:** the mandatory, highest-risk feature — live map tracking during `STARTED`→`IN_PROGRESS`.

- `LocationPing` model + ping endpoint (driver → server).
- Passenger-side polling endpoint for latest location (3–5s interval) rendered on a Leaflet/Maps map with pickup/destination markers + ETA.
- Enforce the tracking window (`STARTED` to `COMPLETED` only) and per-trip access control.
- **Only after this works reliably on polling:** optionally upgrade to Django Channels/WebSocket per `architecture.md` ADR-2, behind a feature flag so polling remains a fallback for the demo.

**Exit criteria:** starting a trip in one browser session visibly moves a marker on the map in a second session within a few seconds, and tracking stops rendering once the trip is completed.

## Phase 6 — Payments & Wallet
**Goal:** a completed trip can be paid for via Cash, Wallet, Card, or UPI (test mode), and Trip status finishes its lifecycle.

- `Wallet`, `WalletTransaction`, `Payment` models.
- Trip auto-transitions to `PAYMENT_PENDING` on completion.
- Cash flow (driver marks received), Wallet flow (atomic debit), Card/UPI via Razorpay Test Mode order-create → Checkout.js → server-side signature verify (per `rules.md` §5 — non-negotiable).
- Wallet recharge flow (same Razorpay pattern, credit on verified success).
- "Payment" and "Wallet" screens.

**Exit criteria:** a completed trip can be paid through each of the four methods in test mode; wallet balance updates correctly; a double-submit or client-spoofed "success" cannot mark a payment as successful without server verification.

## Phase 7 — Ride History, Reports & Settings
**Goal:** everything already happening gets surfaced as history and aggregate insight; Settings hub ties screens together.

- Ride History list (derived from completed `Trip`s, read-only).
- Personal reports: total trips, total distance, estimated fuel consumption, cost/km, efficiency trend — computed via a service function, cached/precomputed via Celery if it gets slow.
- Admin org-level reports: participation, vehicle-wise cost analysis.
- Settings hub screen linking My Trips / My Vehicle / Payment Methods / Ride History / Saved Places / Help & Support / Chat.
- `SavedPlace` CRUD (Home/Office/custom), pre-fills Find/Offer Ride forms.

**Exit criteria:** all Mandatory Feature checklist items in `prd.md` §8 are checked off and demoable end-to-end per `prd.md` §11.

## Phase 8 — Polish, Hardening, Bonus Features
**Goal:** spend remaining time on demo polish and, only after that, bonus features — in priority order.

1. Visual polish pass against `design.md` (spacing, empty states, error states, responsive check at ~360px).
2. `seed_demo_data` finalized so a fresh environment can be demoed in under a minute without manual setup.
3. Notifications (in-app first).
4. Ride Cancellation (seat release + refund-to-wallet).
5. Enhanced Analytics (CO₂/cost-saved-vs-solo).
6. Intelligent Ride Matching, Route Optimization, real push notifications — only if time genuinely remains.

**Exit criteria:** the Phase 8 items are additive; if time runs out here, the product is still fully demoable from the end of Phase 7.

## Suggested Time Allocation (adapt to actual hackathon length)

| Phase | % of total time |
|---|---|
| 0 | 5% |
| 1 | 10% |
| 2 | 5% |
| 3 | 20% |
| 4 | 15% |
| 5 | 15% |
| 6 | 15% |
| 7 | 10% |
| 8 | remaining buffer |

If the clock runs out mid-phase, stop at the nearest **Exit criteria** above so what exists is always a coherent, demoable slice — never leave the app in a broken intermediate state.
