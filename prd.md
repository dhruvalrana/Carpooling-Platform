# PRD.md — Enterprise Carpooling Platform

## 1. Overview

**Project name:** Enterprise Carpooling Platform (working name — rename freely)
**Context:** Odoo Hackathon submission
**Stack constraint:** Full-stack Django (Django templates + Django REST Framework for AJAX/real-time endpoints; no separate SPA framework required)

Daily commuting is expensive, congested, and carbon-heavy. Employees at the same company frequently travel similar routes at similar times but have no structured way to coordinate shared rides. This platform lets employees of a registered organization find or offer rides, track trips live, chat/call during a trip, and pay through cash, card, UPI, or an in-app wallet — with an admin layer per organization and a reporting dashboard for cost/impact analysis.

## 2. Goals

- Ship a working, demoable, end-to-end carpooling flow within the hackathon time box.
- Cover every "Mandatory Feature" listed in the problem statement without exception.
- Keep the system multi-tenant (multiple organizations, isolated data) from day one — retrofitting tenancy later is expensive.
- Prioritize a working real-time trip-tracking + chat loop, since it's explicitly called out as mandatory and is the highest technical risk.

## 3. Non-goals (for the hackathon build)

- Real payment settlement — Razorpay **Test Mode** only, no real money.
- Native mobile apps — responsive web only (Django templates, mobile-first CSS).
- Production-grade horizontal scaling, multi-region deploy, SOC2/compliance work.
- Full route optimization / carpool-matching ML — a simple radius + time-window match is sufficient; "Intelligent Ride Matching" is a bonus feature, not mandatory.
- Push notifications infra (APNs/FCM) — in-app + email notification is enough unless time allows.

## 4. Personas / User Roles

### 4.1 Company Administrator
Manages org-wide config, not day-to-day rides.
- Manage employee records (CRUD, activate/deactivate).
- Manage registered vehicles & driver info (view/audit, not create on behalf of employees).
- Configure org-specific settings: fuel cost/km, currency, service area, cost-per-km formula.
- Monitor employee participation (dashboard).
- Grant/revoke platform access per employee.
- **Cannot** book, publish, or manage rides.

### 4.2 Employee
Single role, dual capability (driver and/or passenger — not separate accounts).
- Register/manage own profile.
- Register/manage own vehicle(s).
- Find a Ride (search, book).
- Offer a Ride (publish, manage bookings on own ride).
- View/manage My Trips.
- Live-track an active trip.
- Chat/call the other trip participant.
- Pay for completed rides; manage wallet.
- View ride history and personal reports.

## 5. Functional Requirements (traced to source doc §5–6)

### FR-1 Authentication & Onboarding
- Splash screen → Login / Sign Up.
- Sign-up requires a valid organization (via invite code, company email domain, or admin-provisioned account — **decide one mechanism in Phase 1**, recommend company email domain allow-list for hackathon simplicity).
- Profile creation (name, phone, photo, emergency contact optional).
- Session-based or JWT auth — recommend Django's session auth for template pages + DRF `SessionAuthentication` for AJAX, avoids double auth systems.

### FR-2 Company Administration
- Admin dashboard: employee list, vehicle list, org settings form, participation metrics.
- Org settings: fuel cost/km, default currency, max ride radius, booking cutoff window.
- Admin is scoped strictly to their own organization (enforced at query level, not just UI).

### FR-3 Find a Ride
- Search form: pickup, destination, date, time, seats needed, recurring toggle.
- Route confirmation screen (calculated route shown before search executes).
- Results list: driver, route, departure time, seats available, fare/seat.
- Instant booking (no driver approval step required for MVP — confirm this assumption; if approval is desired, becomes a bonus/stretch item).

### FR-4 Offer a Ride
- Requires ≥1 registered vehicle before publish is allowed (hard gate).
- Publish form: pickup, destination, date & time, seats, fare/seat.
- Route confirmation before the ride goes live.

### FR-5 Trip Management
- "My Trips" list (upcoming, active, completed, filterable by driver/passenger view).
- Trip detail: driver/passenger details, vehicle info, pickup/drop, schedule, fare, status.
- Trip lifecycle (state machine — see architecture.md §5):
  `BOOKED → STARTED → IN_PROGRESS → COMPLETED → PAYMENT_PENDING → PAYMENT_COMPLETED`
- In-trip chat and voice call between driver and passenger(s).

### FR-6 Live Trip Tracking (mandatory, highest risk)
- Interactive map, live vehicle location, current route, ETA, pickup/destination markers, current status.
- Tracking window: from `STARTED` to `COMPLETED` only — no location sharing outside that window.
- Driver's device pushes location; passenger(s) subscribe and receive updates in near-real-time.

### FR-7 Payments & Wallet
- Payment methods: Cash, Card, UPI, Wallet.
- Card/UPI routed through Razorpay Test Mode.
- Wallet: view balance, recharge (via Razorpay test), pay from balance.
- Payment only unlockable after trip status = `COMPLETED`.

### FR-8 Ride History
- Immutable log per completed trip: participants, route, vehicle, date/time, status, fare, payment method.

### FR-9 Vehicle Management
- CRUD on own vehicles: model, registration number, seating capacity.
- Only the vehicle owner's own registered vehicles are selectable when publishing a ride.

### FR-10 Reports & Analytics
- Personal: total trips, total distance, estimated fuel consumed, cost/km, fuel efficiency trend.
- Org (admin view): aggregate participation, aggregate cost savings, vehicle-wise cost analysis.

### FR-11 Settings
- Quick links: My Trips, My Vehicle, Payment Methods, Ride History, Saved Places, Help & Support, Chat.
- Saved Places: named pickup/destination shortcuts (Home, Office, custom).

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Multi-tenancy | Every query scoped by `organization_id`; no cross-org data leakage, enforced in querysets/managers, not just templates. |
| Real-time latency | Location updates visible to the passenger within ~3–5s of driver ping (WebSocket, not polling, once time allows). |
| Security | Role-based access control (Admin vs Employee) enforced server-side on every view/endpoint, not just hidden UI. |
| Auditability | Trip status transitions and payment events are logged, not just overwritten. |
| Availability | Single-region deploy is acceptable for hackathon; no HA requirement. |
| Data integrity | A ride can never be booked past its seat capacity — enforce with a DB constraint or `select_for_update`, not just app-level checks. |
| Accessibility | Forms keyboard-navigable, visible focus states, reasonable color contrast (see design.md). |
| Browser support | Modern evergreen browsers, mobile-responsive down to ~360px width. |

## 7. Assumptions (carried from source doc, made explicit)

- Multiple organizations, each with its own users and one or more admins.
- Only authenticated users of a registered org can access the platform.
- One driver, one-or-more passengers per ride, bounded by seat capacity.
- A vehicle must exist before a ride can be published.
- Mapping via Google Maps JS API, OpenStreetMap/Leaflet, or Mapbox — pick one in Phase 1 and don't switch mid-build (see architecture.md §6 for the trade-off and recommendation).
- Location sharing is active only during an active trip.
- Payments via Razorpay Test Mode; no real settlement.
- Reports are derived from trip/vehicle/travel data already captured by the app — no external data sources.

## 8. Mandatory Feature Checklist (must all be demoable)

- [ ] Authentication (login/signup/profile)
- [ ] Ride Discovery (Find a Ride + search + matching)
- [ ] Ride Publishing (Offer a Ride)
- [ ] Route Confirmation (both flows)
- [ ] Ride Booking
- [ ] Trip Management (lifecycle + chat/call)
- [ ] Live Trip Tracking
- [ ] Vehicle Management
- [ ] Payments & Wallet (test mode)
- [ ] Ride History
- [ ] Reports Dashboard

## 9. Bonus Features (only after the above are solid)

1. Ride Notifications (in-app first, push if time allows)
2. Ride Cancellation (with seat release + refund-to-wallet logic)
3. Intelligent Ride Matching (score by route overlap + time proximity)
4. Route Optimization (multi-stop ordering)
5. Enhanced Analytics (CO₂ saved, cost-saved-vs-solo-drive)
6. Real-time Push Notifications (web push)

## 10. Open Questions for the Team (resolve in Phase 0)

1. Org onboarding mechanism: invite code vs. email-domain allow-list vs. admin-provisioned accounts?
2. Is driver approval required before a booking is confirmed, or is booking instant?
3. Which map provider — Google Maps (best UX, needs billing key) vs. Leaflet + OSRM (free, hackathon-friendly, no API key friction)?
4. Voice call: real WebRTC integration, or is a "Call" button that deep-links to the phone dialer acceptable for the demo?
5. Recurring rides — full recurrence engine, or a simplified "repeat next 5 weekdays" flag?

## 11. Success Criteria for the Hackathon Demo

- A judge can, in one sitting: sign up as an employee, register a vehicle, offer a ride, and in a second browser/session book that ride as a different employee, watch live tracking move, complete the trip, and pay via wallet — with the ride appearing in history and the report dashboard updating.
- Admin can log in separately, see the org's employees/vehicles, and see aggregate participation.
