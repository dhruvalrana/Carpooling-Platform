# DESIGN.md — Visual & UX Design System

## 1. Design Brief (self-set, since the source doc leaves this open)

**Subject:** an enterprise tool colleagues open twice a day, at the edges of a commute — half-asleep before work, tired after. It has to read instantly, work one-handed on a phone, and feel like infrastructure (transit maps, signage, timetables), not like a consumer ride-hailing app it's competing with on nights out.
**Audience:** employees of a registered company, plus one company admin per org.
**The page's one job, per screen:** get pickup/destination confirmed and a route locked in as fast as possible — everything else (chat, wallet, history) is secondary and can be quieter.

Direction: **wayfinding / transit-map aesthetic**, not ride-hailing-app-neon. Think station signage, printed timetables, dashed route lines on a map — ordered, legible, slightly analog-technical. This also deliberately steers away from the generic AI-design defaults (no cream+terracotta, no near-black+neon-accent, no broadsheet hairline-rules layout).

## 2. Design Tokens

### Color
| Token | Hex | Use |
|---|---|---|
| `--ink` | `#151A2E` | Primary text, dark-mode background |
| `--paper` | `#F6F6F2` | Light-mode background (slightly warm off-white, like timetable paper) |
| `--surface` | `#FFFFFF` | Cards, form surfaces on light mode |
| `--transit-blue` | `#2B3A67` | Primary brand / primary buttons / active nav |
| `--route-amber` | `#E8A33D` | Route lines on map, primary CTA accent, "in progress" states — the signature color |
| `--eco-teal` | `#2E8B74` | Success, "completed," savings/eco stats |
| `--alert-rust` | `#C1503E` | Errors, cancellations — used sparingly |
| `--line-grey` | `#D8D9D4` | Dividers, dashed route-line default color, disabled states |

Dark mode (optional, for the "Live Trip Tracking" screen specifically, where a driver may be using it at night): swap `--paper`/`--surface` for `--ink` and a slightly lifted `#1E2440`, keep `--route-amber` and `--eco-teal` as-is (they read well on dark).

### Typography
| Role | Face | Notes |
|---|---|---|
| Display / headings | **Space Grotesk** | Geometric, slightly mechanical — reads like wayfinding signage, used for screen titles and big numbers (fare, ETA, seats). |
| Body / UI | **Inter** | Neutral, highly legible at small sizes for forms and lists. |
| Data / mono | **IBM Plex Mono** | Route codes, timestamps, registration numbers, fare figures in tables — gives the "timetable" texture. |

Type scale (rem, mobile-first, scale up ~1.125× at desktop breakpoint):
`display-lg 2.25 / display 1.75 / heading 1.25 / body 1 / caption 0.8125 / mono-data 0.9375`

### Layout
- 8px base spacing unit.
- Card radius: `6px` — soft enough to feel modern, restrained enough to still feel "official," not a consumer app.
- Max content width `1120px` on desktop; single-column, full-width on mobile (≤600px).
- Bottom tab bar on mobile for the five primary destinations (Home/Find/Offer/Trips/Settings); left rail nav on desktop.

## 3. Signature Element: The Route Line

The one memorable device, used consistently across the product:

A **dashed horizontal/vertical line with stop-markers** — visually identical whether it appears on the actual map (the route between pickup and destination) or as UI chrome elsewhere:

- **Trip status stepper** (on Trip Detail): rendered as literal stops along a dashed route line — `Booked ⸺ Started ⸺ In Progress ⸺ Completed ⸺ Paid` — the completed segment fills solid `--route-amber`, the remaining segment stays dashed `--line-grey`. This directly reuses the trip lifecycle from `architecture.md` §5, so the UI encodes real state, not decoration.
- **Route Confirmation screen**: the same dashed line connects the pickup pin to the destination pin above the map preview, before the real map route is drawn — a visual promise that resolves into the actual map line below it.
- **Empty states**: a short dashed line with a pin at one end and a "?" marker at the other (e.g., "No rides yet — search a destination to see one appear here").

This is the one place the design takes a real swing; everywhere else stays quiet and functional per the frontend-design principle of spending boldness in a single place.

## 4. Screen Inventory (mapped to `prd.md` FRs)

| Screen | Notes |
|---|---|
| Splash | Wordmark + route-line signature animating in once, then resolves to Login. Keep it under ~1s — this is a tool, not a brand moment. |
| Login / Sign Up | Single column, generous spacing, org detection (email domain or invite code per Phase 0 decision) shown as an inline hint under the email field. |
| Profile Creation | Minimal — name, phone, photo optional. |
| Employee Dashboard | Two big entry cards: "Find a Ride" / "Offer a Ride," plus an upcoming-trip strip and a savings stat (`--eco-teal`) using the mono data face. |
| Admin Dashboard | Employee count, vehicle count, participation chart, org settings link — data-forward, table-heavy, mono face for figures. |
| Find Ride | Form → Route Confirmation → Available Rides list (cards: driver, route-line mini-preview, time, seats, fare in mono). |
| Route Confirmation | Dashed route-line + map preview, editable pickup/destination pins. |
| Available Rides | List/cards, sortable by time/fare/distance. |
| Offer Ride | Form, vehicle picker (blocks with "Register a vehicle first" empty state if none exist), same route-confirmation step. |
| My Vehicle | Card grid of registered vehicles; add-vehicle form. |
| My Trips | Tabs: Upcoming / Active / Completed. Driver vs. passenger view uses the same layout with a small role tag. |
| Trip Detail | Route-line stepper (signature element) at top, map (only rendered when `STARTED`/`IN_PROGRESS`), participant card, chat panel, fare summary. |
| Live Tracking (within Trip Detail) | Full-width map, ETA in mono display type, pickup/destination pins, dark-mode-capable. |
| Chat | Simple two-column message list, timestamps in mono/caption size. |
| Payment | Method selector (Cash/Card/UPI/Wallet) as large tappable cards, fare shown in display type. |
| Wallet | Balance in display type + mono, transaction list, recharge CTA. |
| Ride History | Table on desktop, stacked cards on mobile, one row per completed trip. |
| Reports Dashboard | Chart-forward: trips over time, cost/km trend, fuel-efficiency trend — use `--transit-blue` for primary series, `--eco-teal` for savings series. |
| Settings | Simple list of links (My Trips, My Vehicle, Payment Methods, Ride History, Saved Places, Help & Support, Chat). |
| Saved Places | List with label + mini map pin, add/edit/delete. |

## 5. Component Notes

- **Buttons**: primary = `--transit-blue` fill / white text; CTA-emphasis (Book, Publish, Pay) = `--route-amber` fill / `--ink` text — reserve amber specifically for the single most important action on a screen, don't spread it across every button.
- **Status badges**: use the route-line stepper colors consistently — dashed grey (pending/future), solid amber (active/in progress), solid teal (completed/success), solid rust (cancelled/failed).
- **Maps**: keep map chrome minimal — hide default provider clutter where the API allows, style the route line to match `--route-amber` so the "real" map route visually continues the UI's dashed-line motif.
- **Forms**: label above field, inline validation below field in `--alert-rust`, never rely on placeholder text as a label.
- **Empty states**: always actionable — one line explaining what's missing, one button to fix it (per the frontend-design skill's guidance: an empty screen is an invitation to act, not just a null state).

## 6. Copy Voice

- Plain, active voice, addressed to what the person controls: "Publish your ride," not "Ride submission successful."
- Button label and resulting confirmation use the same verb: "Book ride" → toast reads "Ride booked," not "Booking successful."
- Errors state what happened and how to fix it, without apologizing or being vague: "This ride is full. Try a nearby time or route." not "Something went wrong."
- Never name things by backend structure: a person "books a ride," not "creates a trip object."

## 7. Accessibility & Responsiveness Floor

- Color contrast: body text on `--paper`/`--surface` meets WCAG AA at minimum; `--route-amber` is never used for body text on white (decorative/accent only).
- All interactive elements have a visible keyboard focus ring (don't strip `outline` without replacing it).
- Map-based screens include a non-map fallback list (e.g., ETA and status as text) for screen-reader users and slow connections.
- Respect `prefers-reduced-motion` — the splash-screen line animation and any stepper transitions should have a reduced/instant variant.
- Mobile-first breakpoints: `360px` (small phone) → `600px` (large phone/tablet) → `900px` (desktop) → `1120px` (max content width, centered beyond that).

## 8. What to Avoid

- Don't default to a generic ride-hailing look (rounded pill buttons everywhere, bright single-accent-on-black) — this is enterprise infrastructure software first.
- Don't over-animate; the route-line motif is the one signature moment — keep hover/tap feedback subtle everywhere else.
- Don't invent new colors per screen — every screen pulls from the token table in §2 only.
