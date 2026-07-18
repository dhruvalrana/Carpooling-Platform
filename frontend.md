# Frontend Plan — Enterprise Carpooling Platform

## 1. Stack Decision

Since the whole app is being built "using Django," the simplest hackathon-friendly path is:

- **Django Templates + Bootstrap 5 (or Tailwind) + vanilla JS/HTMX** for server-rendered pages.
- **HTMX + Alpine.js** for the interactive bits (live seat updates, chat, trip status) without needing a separate React/Vue build — keeps one codebase, one deploy, fast to demo.
- **Leaflet.js + OpenStreetMap** (free, no billing setup) or **Google Maps JS API** if you already have a key, for route confirmation + live tracking screens.
- **Chart.js** for the Reports & Analytics dashboard.
- **Django Channels (WebSockets)** only if you want *true* live tracking; otherwise poll every 5–10s with HTMX `hx-trigger="every 8s"` — much faster to build for a hackathon.

> Recommendation for hackathon timeline: skip Channels, use HTMX polling for tracking + chat. Swap to Channels later if time allows (see backend.md "Stretch" section).

---

## 2. Design Direction — "Sunrise Commute" (Light Mode)

Most carpool apps default to black/yellow (Ola/Uber) or blue/white (BlaBlaCar). To stand out, use a **warm, eco-commute palette**: teal (trust/movement) + coral-amber (energy/CTA) on a soft cream base — light mode only, no dark variant needed.

| Token | Hex | Use |
|---|---|---|
| `--color-primary` | `#0F6B66` (deep teal) | Nav bar, primary buttons, active states, map route line |
| `--color-primary-light` | `#E4F2F0` | Selected chips, hover backgrounds |
| `--color-accent` | `#FF8B5E` (warm coral) | Primary CTA buttons ("Find Ride", "Publish Ride"), badges |
| `--color-accent-hover` | `#F0723F` | Button hover/active |
| `--color-bg` | `#FBF8F3` (soft cream) | Page background |
| `--color-surface` | `#FFFFFF` | Cards, modals, inputs |
| `--color-border` | `#E8E2D8` (light sand) | Card borders, dividers |
| `--color-text-primary` | `#1F2937` (charcoal) | Headings, body text |
| `--color-text-secondary` | `#6B7280` (slate) | Helper text, labels |
| `--color-success` | `#4CAF7D` (sage green) | Trip completed, payment success |
| `--color-warning` | `#F5A623` (amber) | Payment pending, in-progress |
| `--color-error` | `#E5533C` | Cancellations, errors |
| `--color-wallet` | `#8B6BB8` (soft violet) | Wallet-specific accents, to visually separate money features |

**Typography:** `Poppins` (headings, 600/700 weight) + `Inter` (body, 400/500). Rounded, friendly, modern — avoids the "corporate SaaS" blue-gray feel.

**Shape language:** 12–16px border radius on cards/buttons, soft shadows (`0 2px 12px rgba(15,107,102,0.08)`), pill-shaped status badges, route lines drawn with a dashed teal path and coral start/end pins.

---

## 3. Site Map / Screens (from PDF §5)

```
/                       → Splash / redirect to login or dashboard
/accounts/login/
/accounts/signup/
/accounts/profile/
/dashboard/                     → Employee home (Find Ride / Offer Ride CTA cards)

/rides/find/                    → Find Ride form
/rides/find/confirm/            → Route Confirmation (map preview)
/rides/find/results/            → Available Rides list
/rides/offer/                   → Offer Ride form
/rides/offer/confirm/           → Route Confirmation
/vehicles/                      → My Vehicle(s) list
/vehicles/add/

/trips/                         → My Trips (tabs: Upcoming / Ongoing / Completed)
/trips/<id>/                    → Trip detail (driver/passenger info, status, chat/call)
/trips/<id>/track/               → Live Trip Tracking map

/payments/<trip_id>/            → Payment screen (Cash/Card/UPI/Wallet)
/wallet/                        → Wallet balance + recharge + history

/history/                       → Ride History list
/history/<id>/                  → Ride History detail

/reports/                       → Reports & Analytics dashboard (employee-level)
/settings/                      → Settings hub (My Trips, My Vehicle, Payment Methods,
                                   Ride History, Saved Places, Help & Support)
/settings/saved-places/

/admin-panel/                   → Company Administrator dashboard (separate from Django admin)
/admin-panel/employees/
/admin-panel/vehicles/
/admin-panel/config/            → fuel cost, travel cost, org settings
```

---

## 4. Key Screen Notes

### Dashboard (post-login)
Two large cards side by side: **"Find a Ride"** (teal) and **"Offer a Ride"** (coral) — this is the core fork in the workflow (PDF §4, step 3). Below: "My Upcoming Trips" strip and a wallet balance chip in the top nav.

### Route Confirmation (shared by Find & Offer)
Map centered on pickup→destination with a drawn route, ETA/distance summary card, and a "Confirm & Search" / "Confirm & Publish" button. This screen is reused by both flows per the PDF workflow — build it as one shared template/component with a `mode` flag.

### Available Rides (Find Ride results)
Card list: driver avatar/name, rating (optional), route summary, departure time, seats left (as filled/empty seat icons), fare per seat (coral highlight), "Book" button. Sort/filter bar on top (time, fare, seats).

### Trip Detail / Lifecycle
Horizontal stepper showing: Ride Booked → Trip Started → In Progress → Completed → Payment Pending → Payment Completed, using teal (done), coral (current), gray (pending) states.

### Live Tracking
Full-bleed map, floating bottom sheet with ETA, driver/vehicle mini-card, chat + call icon buttons (fixed bottom-right).

### Wallet & Payments
Wallet balance as a big card (violet accent) with "Recharge" CTA; payment method selection as a radio-card grid (Cash / Card / UPI / Wallet), each with its own icon.

### Reports & Analytics
KPI cards row (Total Trips, Total Distance, Fuel Saved, Cost/km) + two charts: monthly trips (bar) and cost trend (line) using Chart.js, teal/coral/sage color set.

### Company Admin Panel
Distinct layout (sidebar nav instead of top nav) so it visually reads as a different role context — keep same palette but swap primary accent usage to reduce confusion between "employee mode" and "admin mode."

---

## 5. Component Inventory (reusable Django template partials)

- `_navbar.html` (role-aware: employee vs admin)
- `_ride_card.html`
- `_trip_status_stepper.html`
- `_map_widget.html` (Leaflet init wrapper, takes pickup/destination/live-point as data attrs)
- `_vehicle_card.html`
- `_payment_method_selector.html`
- `_wallet_balance_card.html`
- `_kpi_card.html`
- `_chat_panel.html` (HTMX-polled message list + form)
- `_toast.html` (success/error notifications)
- `_empty_state.html` (no rides found, no trips yet, etc.)

---

## 6. Responsiveness

Mobile-first (most employees will use this on phone during commute hours): single-column stacks, bottom sheet pattern for map details, sticky bottom CTA bar on Find/Offer/Book screens. Desktop gets a two-column layout (map + list side by side) on Find Ride results.

---

## 7. Build Order (frontend)

1. Base template + design tokens (CSS vars) + navbar/footer
2. Auth screens (login/signup/profile)
3. Dashboard
4. Vehicle management (needed before Offer Ride works)
5. Offer Ride + Route Confirmation
6. Find Ride + Results + Booking
7. My Trips + Trip Detail + Stepper
8. Live Tracking + Chat
9. Payments + Wallet
10. Ride History
11. Reports & Analytics
12. Settings + Saved Places
13. Admin Panel
